"""One-command project initialization: auth + CLAUDE.md + daemon."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from codingagentim import config

if TYPE_CHECKING:
    from rich.console import Console

CLAUDE_MD_TEMPLATE = """\
# {project_name}

## 钉钉 Bridge 通知

**每次会话启动时**，设置一个每分钟执行的 cron 任务来同步钉钉 bridge 活动到任务列表：

Cron prompt:
```
调用 check_notifications MCP tool 检查钉钉新通知。如果返回非空列表，对每条记录：type=received 的创建 in_progress 任务（格式"钉钉: sender「text」"），type=completed 的找到对应任务标记完成并在描述中附上 result 摘要，type=failed 的找到对应任务添加失败备注。空列表则静默不输出。
```

## Bridge 守护进程

Bridge 通过 macOS launchd 管理，开机自启 + 崩溃自恢复：

- 状态: `codingagentim daemon status` 或 `get_bridge_status` MCP tool
- 重启: `codingagentim daemon restart`
- 日志: `~/.codingagentim/bridge.{{out,err}}.log`
"""


def run_init(
    project_dir: Path,
    mode: str,
    model: str,
    skip_daemon: bool,
    skip_auth: bool,
    console: Console,
) -> None:
    console.print("[bold]CodingAgentIM 初始化[/bold]\n")

    # --- Step 1: Auth ---
    if not skip_auth:
        _setup_auth(console)

    # --- Step 2: CLAUDE.md ---
    _setup_claude_md(project_dir, console)

    # --- Step 3: Hook ---
    _setup_hook(console)

    # --- Step 4: MCP Server ---
    _setup_mcp_server(console)

    # --- Step 5: Daemon ---
    if not skip_daemon:
        _setup_daemon(mode, model, project_dir, console)

    console.print("\n[bold green]✓ 初始化完成[/bold green]")
    console.print("  钉钉发消息试试！Bridge 会自动处理并在 Claude Code 中显示。")


def _setup_auth(console: Console) -> None:
    cfg = config.load_config()
    dt = cfg.get("dingtalk", {})
    has_key = bool(dt.get("app_key"))
    has_secret = bool(dt.get("app_secret"))

    if has_key and has_secret:
        console.print(f"[green]✓[/green] 钉钉凭证已配置 (app_key: {dt['app_key'][:8]}...)")
        return

    console.print("[yellow]→[/yellow] 配置钉钉凭证")
    app_key = typer.prompt("  DingTalk App Key")
    app_secret = typer.prompt("  DingTalk App Secret", hide_input=True)
    robot_code = typer.prompt("  Robot Code (可选，回车跳过)", default="")

    cfg.setdefault("dingtalk", {})
    cfg["dingtalk"]["app_key"] = app_key
    cfg["dingtalk"]["app_secret"] = app_secret
    if robot_code:
        cfg["dingtalk"]["robot_code"] = robot_code
    config.save_config(cfg)
    console.print(f"[green]✓[/green] 凭证已保存到 {config.CONFIG_FILE}")


def _setup_claude_md(project_dir: Path, console: Console) -> None:
    claude_md = project_dir / "CLAUDE.md"
    project_name = project_dir.name

    section_marker = "## 钉钉 Bridge 监控"
    bridge_section = CLAUDE_MD_TEMPLATE.format(project_name=project_name)

    if claude_md.exists():
        existing = claude_md.read_text()
        if section_marker in existing:
            console.print("[green]✓[/green] CLAUDE.md 已包含 Bridge 监控配置")
            return
        content = existing.rstrip() + "\n\n" + bridge_section.split("\n", 2)[2]
        claude_md.write_text(content)
        console.print("[green]✓[/green] CLAUDE.md 已追加 Bridge 监控配置")
    else:
        claude_md.write_text(bridge_section)
        console.print(f"[green]✓[/green] 已创建 {claude_md}")


def _setup_hook(console: Console) -> None:
    import json

    hook_script = Path(__file__).resolve().parent.parent.parent / "scripts" / "bridge-notify-hook.js"
    if not hook_script.exists():
        import importlib.resources
        console.print(f"[yellow]⚠[/yellow] Hook 脚本未找到: {hook_script}")
        return

    settings_file = Path.home() / ".claude" / "settings.json"
    if not settings_file.exists():
        console.print("[yellow]⚠[/yellow] ~/.claude/settings.json 未找到，跳过 hook 注册")
        return

    try:
        settings = json.loads(settings_file.read_text())
    except (json.JSONDecodeError, OSError):
        console.print("[yellow]⚠[/yellow] settings.json 解析失败")
        return

    hook_cmd = f"node {hook_script}"
    hooks = settings.setdefault("hooks", {})
    usp_hooks = hooks.setdefault("UserPromptSubmit", [])

    for entry in usp_hooks:
        for h in entry.get("hooks", []):
            if "bridge-notify-hook" in h.get("command", ""):
                console.print("[green]✓[/green] 通知 Hook 已注册")
                return

    usp_hooks.append({
        "hooks": [{
            "type": "command",
            "command": hook_cmd,
            "timeout": 3,
        }]
    })

    settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False))
    console.print(f"[green]✓[/green] 通知 Hook 已注册到 ~/.claude/settings.json")


def _setup_mcp_server(console: Console) -> None:
    import json
    import shutil

    codingagentim_bin = shutil.which("codingagentim")
    if not codingagentim_bin:
        venv_bin = Path(__file__).resolve().parent.parent.parent / ".venv" / "bin" / "codingagentim"
        if venv_bin.exists():
            codingagentim_bin = str(venv_bin)

    if not codingagentim_bin:
        console.print("[yellow]⚠[/yellow] codingagentim 命令未找到，跳过 MCP Server 注册")
        return

    settings_file = Path.home() / ".claude" / "settings.json"
    if not settings_file.exists():
        console.print("[yellow]⚠[/yellow] ~/.claude/settings.json 未找到，跳过 MCP Server 注册")
        return

    try:
        settings = json.loads(settings_file.read_text())
    except (json.JSONDecodeError, OSError):
        console.print("[yellow]⚠[/yellow] settings.json 解析失败")
        return

    mcp_servers = settings.setdefault("mcpServers", {})
    if "codingagentim" in mcp_servers:
        console.print("[green]✓[/green] MCP Server 已注册")
        return

    mcp_servers["codingagentim"] = {
        "command": codingagentim_bin,
        "args": ["mcp", "serve"],
    }

    settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False))
    console.print(f"[green]✓[/green] MCP Server 已注册到 ~/.claude/settings.json")


def _setup_daemon(mode: str, model: str, project_dir: Path, console: Console) -> None:
    from codingagentim.daemon import install, is_loaded, get_status

    if is_loaded():
        info = get_status()
        pid = info.get("pid")
        if pid:
            console.print(f"[green]✓[/green] Daemon 已运行 (PID={pid})")
            return

    console.print("[yellow]→[/yellow] 安装 Bridge 守护进程...")
    plist_path = install(mode=mode, model=model, work_dir=str(project_dir))
    console.print(f"[green]✓[/green] Daemon 已安装: {plist_path}")
    console.print("  开机自启 + 崩溃自恢复")
