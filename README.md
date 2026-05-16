# CodingAgentIM

IM x AI Coding Agent 双向桥接工具。让 IM 消息直接驱动 AI Coding Agent 执行开发任务。

## 工作流程

```
┌─────────────┐          ┌──────────────────┐          ┌─────────────────┐
│   钉钉用户   │──消息──▶│  Bridge Daemon    │──入队──▶│  Claude Code     │
│             │◀─结果──│  (launchd/inbox)  │◀─回复──│  (活跃会话)       │
└─────────────┘          └──────────────────┘          └─────────────────┘
```

1. 用户通过 IM（钉钉）发送消息
2. Bridge daemon 即时收到，回复确认（「👌 收到，Coding Agent 处理中」）
3. 消息写入 inbox 队列 + notifications 文件
4. Claude Code 会话通过秒级轮询（poll_notifications）获取任务
5. Agent 在本地执行开发工作（写代码、跑测试、分析问题等）
6. 完成后通过 reply_dingtalk 将结果回复给用户

## 特性

- **Inbox 模式**: 消息排队等待活跃 Agent 会话处理，而非自动 fork 子进程
- **秒级响应**: poll_notifications 长轮询，1 秒内感知新消息
- **回复级别**: verbose（话痨）/ normal / quiet（静默），通过 IM 指令动态切换
- **Daemon 守护**: launchd 管理，开机自启 + 崩溃自恢复
- **MCP 工具集**: check_notifications / poll_notifications / reply_dingtalk / get_reply_level / set_reply_level
- **插件架构**: Provider 模式，易于扩展新 IM 平台

## 快速开始

```bash
pip install -e .
codingagentim init
```

`init` 会完成：
1. 配置 IM 凭证（交互式）
2. 创建 `CLAUDE.md`（Agent 行为规范）
3. 安装 bridge daemon（inbox 模式）

## Bridge 模式

| 模式 | 工作方式 | 适用场景 |
|------|---------|---------|
| `inbox` (推荐) | 消息入队，由活跃会话处理 | 需要真正执行开发任务 |
| `cli` | fork claude 子进程 | 简单问答，无需复杂开发 |
| `api` | 直接调用 Anthropic API | 最快响应，无项目上下文 |

```bash
codingagentim daemon install --mode inbox   # 推荐
codingagentim daemon install --mode cli
codingagentim daemon install --mode api --model claude-sonnet-4-20250514
```

## 回复级别

通过钉钉发送指令切换：

| 指令 | 级别 | 行为 |
|------|------|------|
| `/verbose` 或 `话痨` | verbose | 发关键中间进展 + 最终结果 |
| `/normal` 或 `正常` | normal | 发确认 + 最终结果 |
| `/quiet` 或 `静默` | quiet | 只发最终结果 |

## Daemon 管理

```bash
codingagentim daemon install    # 安装并启动
codingagentim daemon status     # 查看状态
codingagentim daemon restart    # 重启
codingagentim daemon logs       # 查看日志
codingagentim daemon uninstall  # 卸载
```

## MCP 工具

通过 `codingagentim mcp serve` 暴露给 AI Agent 使用：

| 工具 | 功能 |
|------|------|
| `check_notifications` | 检查新通知（即时返回） |
| `poll_notifications` | 长轮询（秒级，阻塞等待） |
| `reply_dingtalk` | 回复消息给 IM 用户 |
| `get_reply_level` | 查询当前回复级别 |
| `set_reply_level` | 设置回复级别 |
| `get_bridge_status` | 获取 daemon 状态 |
| `dingtalk_send_message` | 发送消息到群/用户 |
| `dingtalk_search_contact` | 搜索联系人 |
| `dingtalk_create_todo` | 创建待办 |
| `dingtalk_list_calendar` | 查看日历 |

## CLI 参考

```
codingagentim init                     # 一键初始化
codingagentim daemon <cmd>             # 守护进程管理
codingagentim dingtalk bridge          # 前台启动 bridge
codingagentim dingtalk listen          # 启动 dispatcher
codingagentim dingtalk chat send       # 发送消息
codingagentim dingtalk contact search  # 搜索联系人
codingagentim dingtalk calendar list   # 查看日历
codingagentim dingtalk todo create     # 创建待办
codingagentim inbox check|pop|done     # 消息队列管理
codingagentim task list|show|clean     # 任务管理
codingagentim auth login|status        # 凭证管理
codingagentim mcp serve                # 启动 MCP server
codingagentim hook notify              # Hook 通知
```

## 配置

配置文件: `~/.codingagentim/config.toml`

```toml
default_provider = "dingtalk"
default_agent = "claude"
reply_level = "normal"

[dingtalk]
app_key = "your_app_key"
app_secret = "your_app_secret"
robot_code = "your_robot_code"
```

---

## Roadmap

### IM 平台支持

| 平台 | 状态 | 说明 |
|------|------|------|
| 钉钉 (DingTalk) | ✅ 已完成 | Stream 协议，单聊/群聊 |
| 飞书 (Feishu/Lark) | 🔜 计划中 | Event Subscription |
| 企业微信 (WeCom) | 🔜 计划中 | 回调模式 |
| 微信 (WeChat) | 🔜 计划中 | 需要第三方框架 |

### AI Coding Agent 支持

| Agent | 状态 | 说明 |
|-------|------|------|
| Claude Code | ✅ 已完成 | MCP 集成 + CLI resume/fork |
| Codex (OpenAI) | 🔜 计划中 | CLI 集成 |
| Gemini CLI | 🔜 计划中 | Google AI |
| Cursor | 🔜 计划中 | IDE Agent |
| Qodo (原 CodiumAI) | 🔜 计划中 | 代码质量 Agent |

### 功能规划

- [ ] 多 Agent 调度 — 不同类型任务路由到不同 Agent
- [ ] 任务并行 — 多任务队列 + 优先级
- [ ] 上下文记忆 — 记住每个用户的对话历史
- [ ] 文件交互 — 支持 IM 发送文件/图片，Agent 读取处理
- [ ] 进度推送 — 长任务主动推送中间进展
- [ ] Web Dashboard — 任务状态可视化面板

## License

Apache-2.0
