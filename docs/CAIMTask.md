### claude-dingtalk-hooks-integration ###
# agentalk 任务清单

## Phase 1: 项目初始化 + 核心框架

- [x] 创建 GitHub 仓库，初始化 `pyproject.toml`、README、LICENSE
- [x] 实现 `src/codingagentim/__init__.py` + `__main__.py` 入口
- [x] 实现 `src/codingagentim/config.py` — 配置管理（`~/.codingagentim/config.toml`）
- [x] 实现 `src/codingagentim/output.py` — 输出格式化（json/table/raw）
- [x] 实现 `src/codingagentim/auth.py` — 统一认证框架 + keyring 凭证存储
- [x] 实现 `src/codingagentim/core/provider.py` — BaseProvider 基类
- [x] 实现 `src/codingagentim/core/models.py` — 通用数据模型
- [x] 实现 `src/codingagentim/core/registry.py` — Provider 注册与发现
- [x] 实现 `src/codingagentim/cli.py` — Typer 主命令组

## Phase 1.5: 钉钉 Provider（正向链路）

- [x] 实现 `src/codingagentim/providers/dingtalk/auth.py` — App 认证 + token 缓存
- [x] 实现 `src/codingagentim/providers/dingtalk/api.py` — 钉钉 OpenAPI 封装
- [x] 实现 `src/codingagentim/providers/dingtalk/dws.py` — dws CLI 桥接
- [x] 实现 `src/codingagentim/providers/dingtalk/provider.py` — DingTalkProvider
- [x] 实现 `src/codingagentim/providers/dingtalk/services/chat.py` — 消息发送
- [x] 实现 `src/codingagentim/providers/dingtalk/services/contact.py` — 联系人搜索
- [x] 实现 `src/codingagentim/providers/dingtalk/services/calendar.py` — 日程管理
- [x] 实现 `src/codingagentim/providers/dingtalk/services/todo.py` — 待办管理
- [x] 编写 `tests/test_dingtalk_provider.py`

## Phase 2: 反向链路（IM → Agent）

- [x] 实现 `src/codingagentim/core/dispatcher.py` — Agent Dispatcher
- [x] 实现 `src/codingagentim/providers/dingtalk/listener.py` — Stream 监听器
- [x] 在 `cli.py` 中注册 `codingagentim dingtalk listen` 子命令
- [x] 实现结果摘要生成逻辑（PR 链接/diff 统计提取）
- [x] 编写 `tests/test_dispatcher.py`
- [x] 编写 `tests/test_listener.py`

## Phase 3: MCP Server + Hook 集成

- [x] 实现 `src/codingagentim/mcp_server.py` — MCP Server（stdio transport）
- [x] 实现 `src/codingagentim/hooks/notify.py` — Hook 通知入口
- [x] 实现 `src/codingagentim/hooks/adapters.py` — 各工具数据格式适配
- [x] 创建 `hooks/claude-code.json` 模板
- [x] 创建 `hooks/codex-cli.toml` 模板
- [x] 创建 `hooks/gemini-cli.json` 模板
- [x] 编写 `tests/test_mcp_server.py` + `tests/test_hooks.py`

## Phase 4: Agent Skills + 安装分发

- [x] 编写 `skills/SKILL.md` 主 Skill 文档
- [x] 编写 `skills/references/products/dingtalk.md` 产品参考
- [x] 实现 `scripts/install-hooks.sh` — Hook 自动注入
- [x] 实现 `scripts/install-skills.sh` — Skills 安装
- [x] 编写 `README.md` 完整文档（含双向链路说明）
- [x] 发布到 PyPI（包已构建并通过 twine check，执行 `twine upload dist/*` 即可发布）

## 验证

- [x] 手动验证: CLI 正向发送钉钉消息（通过 listen 回复验证，groupMessages/send 200 OK）
- [x] 手动验证: listen 反向接收 @机器人 消息并调度 coding agent（收到王宁 "cc"，回复成功）
- [x] 手动验证: MCP Server 被 AI 工具识别（initialize + tools/list 均正常）
- [x] 手动验证: Hook 自动通知（adapters 正常工作，notify 入口正常）


updateAtTime: 2026/5/15 11:23:46

planId: cf724d74-2a36-48f1-b663-cd13a14f2c19