# CodingAgentIM：给 AI Coding Agent 一个钉钉工位

## 先看效果

<!-- 截图：钉钉对话「写个快排」→ 收到确认 → 收到结果 -->
![钉钉对话效果](./images/demo-quicksort.png)

<!-- 截图：钉钉对话「看看现在还有什么问题」→ 项目状态分析结果 -->
![项目分析效果](./images/demo-analysis.png)

这不是调 API 聊天。这是一个 **AI Coding Agent 在我的项目目录里真正执行了代码编写**，然后把结果发回了我的钉钉。

**三步上手：**

1. 去[钉钉开放平台](https://open-dev.dingtalk.com/)创建应用，开启机器人能力（选 Stream 模式，不需要公网 IP）
2. 安装 + 初始化：
```bash
pip install codingagentim
codingagentim init    # 填入 AppKey / AppSecret
```
3. 开机自启，后面不用管。掏出手机发消息就是在指挥你的 AI 程序员干活。

---

## 为什么做这个

AI Coding Agent 很强，但有个尴尬：**你得坐在电脑前才能用**。

打开终端 → 输入需求 → 等结果 → 检查代码。这套流程把你绑在了工位上。

我在想：能不能让 Agent 像同事一样——**我在钉钉喊一声，它就干活了**？

不管我在开会、在路上、还是在摸鱼，掏出手机发一条钉钉消息，几秒后收到确认，几十秒后收到结果。

## 核心原理

### 为什么不能直接让 IM 调 API

最简单的做法是：钉钉收到消息 → 调 LLM API → 把回复发回去。很多钉钉机器人都这么做。

**但这不是 Coding Agent。** 调 API 只能聊天，不能：
- 读你的项目代码
- 在正确的目录里创建文件
- 跑测试、装依赖
- 用 git 提交代码
- 基于当前项目上下文做判断

真正的 Coding Agent 需要一个**有项目上下文的本地运行环境**。这就是核心矛盾：IM 在云端，Agent 在本地。

### 解法：Bridge + Inbox 队列

CodingAgentIM 的架构是一个**桥接层**：

```
┌────────────────────────────────────────────────────────────────────┐
│                        你的开发机（本地）                            │
│                                                                    │
│  ┌─────────────┐     ┌──────────────┐     ┌───────────────────┐  │
│  │ Bridge      │     │ Inbox Queue  │     │ Claude Code       │  │
│  │ Daemon      │────▶│ (文件队列)    │◀────│ (活跃会话)         │  │
│  │             │     │              │     │                   │  │
│  │ • Stream    │     │ notifications│     │ • 有项目上下文     │  │
│  │   连接钉钉  │     │   .jsonl     │     │ • 能跑测试        │  │
│  │ • 写 inbox  │     │ inbox.json   │     │ • 能写代码        │  │
│  │ • 回复确认  │     │              │     │ • 能 git 操作     │  │
│  └─────────────┘     └──────────────┘     └───────────────────┘  │
│        ▲                                          │               │
│        │                                          │               │
└────────│──────────────────────────────────────────│───────────────┘
         │                                          │
    钉钉 Stream                              reply_dingtalk
    (WebSocket)                              (HTTP API)
         │                                          │
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         钉钉服务器                                │
└─────────────────────────────────────────────────────────────────┘
```

三个组件各司其职：

1. **Bridge Daemon** — 一个常驻进程，通过钉钉 Stream 协议保持 WebSocket 连接。收到消息后**不做任何 AI 处理**，只做两件事：写入 inbox 队列 + 回复「收到」。这保证了亚秒级确认。

2. **文件队列** — 消息以 JSON 写入 `notifications.jsonl`，极简可靠。不用 Redis、不用 RabbitMQ，一个文件搞定进程间通信。

3. **活跃 Agent 会话** — 已经 cd 到你的项目目录、加载了 CLAUDE.md 上下文的 Claude Code 会话。通过 MCP 工具（poll_notifications）每秒轮询队列，发现新任务就执行。

### 为什么是 Inbox 而不是 Fork

早期版本每收到一条消息就 fork 一个新的 `claude` 子进程。问题：

- 子进程没有当前会话的上下文
- 每次冷启动要加载项目，慢
- 回复质量很差（等于每次重新认识你的代码）
- 无法利用之前的对话记忆

Inbox 模式的核心洞察：**让已经在工作状态的 Agent 来接单**，而不是每次从零开始。就像让一个已经熟悉项目的同事接手，vs 每次叫一个新人来。

### 秒级感知：长轮询

Agent 怎么知道有新消息？

```python
async def poll_notifications(timeout=55, interval=1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        notifs = check_file_for_new_data()
        if notifs:
            return notifs
        await asyncio.sleep(interval)
    return []
```

这是一个长轮询（Long Polling）：阻塞等待最多 55 秒，每 1 秒检查一次文件。有新消息立即返回，没有就静默等待。配合 cron 每分钟重启一轮，实现无间断监听。

为什么不用 WebSocket/SSE 推送？因为 Claude Code 的 MCP 协议是请求-响应模式，不支持服务端主动推送。长轮询是在这个约束下的最优解。

### 回复链路：MCP 工具

Agent 完成任务后怎么回复？通过 MCP 工具 `reply_dingtalk`：

```
Agent 调用 reply_dingtalk(sender_id="xxx", content="结果")
    → MCP Server 收到请求
    → 调用 DingTalk OpenAPI 发送消息
    → 用户在钉钉收到结果
```

整个过程对 Agent 来说就是一个工具调用，和它调用 Bash、Read 文件没有区别。

### 回复级别：运行时行为控制

一个有趣的设计：用户可以在钉钉发 `/quiet` 来改变 Agent 的行为模式。这通过文件配置实现：

```
用户发 /quiet → Bridge 拦截 → 写入 config.toml: reply_level = "quiet"
                                                         ↓
Agent 下次执行任务前读取 config → 决定要不要发中间进展
```

本质上是**用户通过 IM 实时调参**。Agent 不是固定行为的机器人，它能被运行时控制。

## 完整数据流（一条消息的一生）

```
时间线：

T+0ms    用户在钉钉发送「快排」
T+50ms   钉钉服务器通过 Stream WebSocket 推送到 Bridge Daemon
T+100ms  Bridge 回复「👌 收到，Coding Agent 处理中」
T+150ms  Bridge 写入 notifications.jsonl: {sender_id, text, type: "received"}
T+1s     Claude Code 的 poll_notifications 检测到新数据
T+1.1s   Claude Code 创建任务、开始执行
T+5s     Agent 写完代码
T+5.5s   Agent 调用 reply_dingtalk 发送结果
T+6s     用户在钉钉收到快排实现
```

端到端 6 秒。瓶颈在 Agent 思考和写代码的时间，而非桥接链路。

## Plugin 架构

IM 端和 Agent 端都是可插拔的：

```
src/codingagentim/
├── core/
│   ├── provider.py      # BaseProvider 抽象类
│   ├── registry.py      # Provider 注册表
│   └── message_queue.py # 通用队列（所有 IM 共用）
├── providers/
│   ├── dingtalk/        # ✅ 钉钉实现
│   ├── feishu/          # 🔜 飞书（待实现）
│   └── wecom/           # 🔜 企业微信（待实现）
└── mcp_server.py        # Agent 接口（MCP 协议）
```

新增一个 IM 平台只需要：
1. 实现 `BaseProvider` 接口（send_message, reply_message, search_contact...）
2. 写一个 Handler（收消息 → 写 inbox）
3. 注册到 registry

Agent 端通过 MCP 工具解耦，任何支持 MCP 的 Agent 都能接入。

## 技术栈

| 组件 | 技术 | 为什么选它 |
|------|------|-----------|
| IM 连接 | 钉钉 Stream (WebSocket) | 官方推荐，无需公网 IP |
| 进程间通信 | 文件队列 (JSONL) | 零依赖，极简可靠 |
| 守护进程 | macOS launchd | 系统级，开机自启+崩溃恢复 |
| Agent 接口 | MCP (stdio) | Claude Code 原生支持 |
| 消息发送 | DingTalk OpenAPI v2 | REST API，简单直接 |
| 配置 | TOML | 人类可读可编辑 |

## 号召：用你的 Coding Agent 来贡献

CodingAgentIM 的 IM 端已经跑通了钉钉，**但 Agent 端目前只支持 Claude Code**。

如果你在用其他 Coding Agent，我们需要你的帮助：

### 🔜 待实现的 Agent 适配

| Agent | 思路 | 难度 |
|-------|------|------|
| **Codex (OpenAI)** | Codex CLI 支持 `--prompt` 模式，可以像 Claude Code 一样通过子进程调用 | ⭐⭐ |
| **qoder** | 有 Agent 模式的 API，需要研究其自动化接口 | ⭐⭐⭐ |
| **Gemini CLI** | Google 的 Gemini CLI 支持类似的 prompt 输入模式 | ⭐⭐ |
| **Cursor** | Cursor 有 Agent 模式的 API，需要研究其自动化接口 | ⭐⭐⭐ |
| **Qodo** | 专注代码质量，可作为 review agent 接入 | ⭐⭐ |
| **Aider** | 开源，CLI 优先，适配应该很直接 | ⭐ |

### 贡献方式

**最酷的方式：让你的 Coding Agent 自己来实现适配。**

1. Fork 本仓库
2. 让你的 Agent 读 `src/codingagentim/providers/dingtalk/` 理解模式
3. 让它按相同架构实现新的 Provider 或 Agent 适配
4. 提 PR

这本身就是对 Coding Agent 能力的验证——如果你的 Agent 连自己的适配层都写不出来，那它大概也不适合接入这个系统。

### 具体适配指南

Agent 适配需要实现的核心能力：

```python
# 你的 agent 需要能被这样调用：
class YourAgentAdapter:
    async def execute(self, prompt: str, work_dir: str) -> str:
        """接收 prompt，在 work_dir 中执行，返回结果文本"""
        ...
```

参考 `handlers/bridge.py` 中 Claude Code 的适配方式：通过 `--resume --fork-session -p <prompt>` 调用 CLI。大多数 Agent 都有类似的非交互模式。

### 待实现的 IM 平台

| IM | 接入协议 | 参考 |
|----|---------|------|
| **飞书** | Event Subscription (HTTP) | 需要公网回调 URL 或内网穿透 |
| **企业微信** | 回调模式 (HTTP) | 类似飞书 |
| **微信** | itchat / WeChatFerry 等第三方 | 非官方，有风险 |
| **Slack** | Events API + Socket Mode | 国际团队适用 |
| **Discord** | Gateway WebSocket | 开源社区适用 |

每个 IM 适配只需实现 `BaseProvider` 接口 + 对应的 Handler。参考 `providers/dingtalk/` 的实现即可。

## 当前的不足（也是优化方向）

坦诚说几个目前的限制：

| 问题 | 原因 | 优化方向 |
|------|------|---------|
| **必须有活跃会话** | Agent 依赖一个正在运行的 Claude Code 会话来执行任务。电脑关了就断了 | 支持 headless 模式，或部署到服务器 |
| **单任务串行** | 一次只能处理一个钉钉任务，前一个没完后一个等着 | 任务队列 + 并行执行 |
| **钉钉侧无多轮对话** | Agent 有项目上下文，但钉钉用户的连续消息之间没有对话串联 | 基于 sender_id 的会话历史管理 |
| **只支持文字** | 不能发图片/文件给 Agent 处理 | 接入钉钉文件下载 API |
| **只支持钉钉** | 不是每个团队都用钉钉 | Plugin 架构已就绪，待实现飞书/企微 |
| **cron 有空闲限制** | Claude Code 的 cron 只在 REPL 空闲时触发，忙的时候消息会延迟 | 用 hook 机制补充 |
| **无权限控制** | 任何人发消息都会被执行 | 加白名单 / 审批流 |
| **结果无法追溯** | 执行结果只在钉钉里，没有持久化记录 | 任务日志 + Web Dashboard |

这些都是已知的、计划解决的问题。如果你对某个方向有想法，欢迎直接 PR。

## 下一步

- **飞书 / 企业微信 / 微信** — 不是每个团队都用钉钉
- **多 Agent 调度** — 代码任务给 Claude，review 给 Qodo，文档给 Gemini
- **任务并行** — 同时处理多个请求
- **上下文记忆** — 连续对话不用重复背景
- **Web Dashboard** — 任务状态可视化
- **跨设备同步** — 手机发、电脑做、手机收

## 试试看

1. [钉钉开放平台](https://open-dev.dingtalk.com/) 创建应用 → 开启机器人 → 选 Stream 模式
2. 安装：
```bash
pip install codingagentim
codingagentim init
```
3. 给机器人发条消息试试。

---

**GitHub**: [MichaelJayW/CodingAgentIM](https://github.com/MichaelJayW/CodingAgentIM)

Apache-2.0 开源。Star 是最好的鼓励，PR 是最好的支持。

让你的 Coding Agent 也来试试？🤖
