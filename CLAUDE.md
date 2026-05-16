# CodingAgentIM

IM x AI Coding Agent 双向桥接工具，当前支持钉钉。

## 项目结构

- `src/codingagentim/` — 核心代码
- `src/codingagentim/providers/dingtalk/` — 钉钉适配层
- `src/codingagentim/daemon.py` — launchd 守护进程管理
- `examples/` — 示例代码

## 开发环境

- Python venv: `.venv/`
- 运行测试: `.venv/bin/python -m pytest tests/ --tb=short`
- 安装依赖: `.venv/bin/pip install -e ".[dev]"`

## 钉钉 Bridge 通知

**每次会话启动时**，设置一个每分钟执行的 cron 任务来同步钉钉 bridge 活动到任务列表：

Cron prompt:
```
调用 check_notifications MCP tool 检查钉钉新通知。如果返回非空列表，对每条记录：type=received 的创建 in_progress 任务（格式"钉钉: sender「text」"），type=completed 的找到对应任务标记完成并在描述中附上 result 摘要，type=failed 的找到对应任务添加失败备注。空列表则静默不输出。
```

## Bridge 守护进程

Bridge 通过 macOS launchd 管理，开机自启 + 崩溃自恢复：

- 安装: `codingagentim daemon install --mode cli`
- 状态: `codingagentim daemon status`
- 重启: `codingagentim daemon restart`
- 卸载: `codingagentim daemon uninstall`
- 日志: `~/.codingagentim/bridge.{out,err}.log`
