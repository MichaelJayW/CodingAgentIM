### claude-dingtalk-hooks-integration ###
# agentalk 任务清单

## Phase 1: 项目初始化 + 核心框架

- [ ] 创建 GitHub 仓库 `agentalk`，初始化 `pyproject.toml`、README、LICENSE
- [ ] 实现 `src/agentalk/__init__.py` + `__main__.py` 入口
- [ ] 实现 `src/agentalk/config.py` — 配置管理（`~/.agentalk/config.toml`）
- [ ] 实现 `src/agentalk/output.py` — 输出格式化（json/table/raw）
- [ ] 实现 `src/agentalk/auth.py` — 统一认证框架 + keyring 凭证存储
- [ ] 实现 `src/agentalk/core/provider.py` — BaseProvider 基类
- [ ] 实现 `src/agentalk/core/models.py` — 通用数据模型
- [ ] 实现 `src/agentalk/core/registry.py` — Provider 注册与发现
- [ ] 实现 `src/agentalk/cli.py` — Typer 主命令组

## Phase 1.5: 钉钉 Provider（正向链路）

- [ ] 实现 `src/agentalk/providers/dingtalk/auth.py` — OAuth + App 认证
- [ ] 实现 `src/agentalk/providers/dingtalk/api.py` — 钉钉 OpenAPI 封装
- [ ] 实现 `src/agentalk/providers/dingtalk/dws.py` — dws CLI 桥接
- [ ] 实现 `src/agentalk/providers/dingtalk/provider.py` — DingTalkProvider
- [ ] 实现 `src/agentalk/providers/dingtalk/services/chat.py` — 消息发送
- [ ] 实现 `src/agentalk/providers/dingtalk/services/contact.py` — 联系人搜索
- [ ] 实现 `src/agentalk/providers/dingtalk/services/calendar.py` — 日程管理
- [ ] 实现 `src/agentalk/providers/dingtalk/services/todo.py` — 待办管理
- [ ] 编写 `tests/test_dingtalk_provider.py`

## Phase 2: 反向链路（IM → Agent）

- [ ] 实现 `src/agentalk/core/dispatcher.py` — Agent Dispatcher
- [ ] 实现 `src/agentalk/providers/dingtalk/listener.py` — Stream 监听器
- [ ] 在 `cli.py` 中注册 `agentalk dingtalk listen` 子命令
- [ ] 实现结果摘要生成逻辑（PR 链接/diff 统计提取）
- [ ] 编写 `tests/test_dispatcher.py`
- [ ] 编写 `tests/test_listener.py`

## Phase 3: MCP Server + Hook 集成

- [ ] 实现 `src/agentalk/mcp_server.py` — MCP Server（stdio transport）
- [ ] 实现 `src/agentalk/hooks/notify.py` — Hook 通知入口
- [ ] 实现 `src/agentalk/hooks/adapters.py` — 各工具数据格式适配
- [ ] 创建 `hooks/claude-code.json` 模板
- [ ] 创建 `hooks/codex-cli.toml` 模板
- [ ] 创建 `hooks/gemini-cli.json` + `hooks/opencode.toml` 模板
- [ ] 编写 `tests/test_mcp_server.py` + `tests/test_hooks.py`

## Phase 4: Agent Skills + 安装分发

- [ ] 编写 `skills/SKILL.md` 主 Skill 文档
- [ ] 编写 `skills/references/products/dingtalk.md` 产品参考
- [ ] 实现 `scripts/install-hooks.sh` — Hook 自动注入
- [ ] 实现 `scripts/install-skills.sh` — Skills 安装
- [ ] 编写 `README.md` 完整文档（含双向链路说明）
- [ ] 发布到 PyPI

## 验证

- [ ] 手动验证: CLI 正向发送钉钉消息
- [ ] 手动验证: listen 反向接收 @机器人 消息并调度 coding agent
- [ ] 手动验证: MCP Server 被 AI 工具识别
- [ ] 手动验证: Hook 自动通知


updateAtTime: 2026/5/15 11:23:46

planId: cf724d74-2a36-48f1-b663-cd13a14f2c19