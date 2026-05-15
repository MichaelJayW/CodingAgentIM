"""CLI entry point — Typer-based command group."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import typer
from rich.console import Console

from codingagentim import __version__, config
from codingagentim.output import output as fmt_output

app = typer.Typer(
    name="codingagentim",
    help="CodingAgentIM — IM x AI Coding Agent bidirectional bridge",
    no_args_is_help=True,
)
console = Console()

# --- DingTalk sub-commands ---

dingtalk_app = typer.Typer(name="dingtalk", help="DingTalk operations", no_args_is_help=True)
app.add_typer(dingtalk_app, name="dingtalk")

chat_app = typer.Typer(name="chat", help="Chat / messaging", no_args_is_help=True)
dingtalk_app.add_typer(chat_app, name="chat")


@chat_app.command("send")
def chat_send(
    to: str = typer.Option(..., "--to", help="Target conversation ID or user ID"),
    text: str = typer.Option(..., "--text", help="Message content"),
    msg_type: str = typer.Option("text", "--type", help="Message type: text or markdown"),
    user: bool = typer.Option(False, "--user", help="Send to user instead of group"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json/table/raw"),
):
    """Send a message via DingTalk robot."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    async def _run():
        provider = DingTalkProvider()
        if user:
            result = await provider.send_to_user([to], text, msg_type)
        else:
            result = await provider.send_message(to, text, msg_type)
        return result

    result = asyncio.run(_run())
    fmt_output(result, format)


contact_app = typer.Typer(name="contact", help="Contact management", no_args_is_help=True)
dingtalk_app.add_typer(contact_app, name="contact")


@contact_app.command("search")
def contact_search(
    query: str = typer.Option(..., "--query", "-q", help="Search keyword"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """Search DingTalk contacts."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    async def _run():
        provider = DingTalkProvider()
        return await provider.search_contact(query, limit)

    results = asyncio.run(_run())
    fmt_output(results, format)


calendar_app = typer.Typer(name="calendar", help="Calendar management", no_args_is_help=True)
dingtalk_app.add_typer(calendar_app, name="calendar")


@calendar_app.command("list")
def calendar_list(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date (YYYY-MM-DD)"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """List calendar events."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    async def _run():
        provider = DingTalkProvider()
        return await provider.list_calendar_events(date)

    results = asyncio.run(_run())
    fmt_output(results, format)


todo_app = typer.Typer(name="todo", help="Todo management", no_args_is_help=True)
dingtalk_app.add_typer(todo_app, name="todo")


@todo_app.command("create")
def todo_create(
    title: str = typer.Option(..., "--title", "-t", help="Todo title"),
    description: str = typer.Option("", "--desc", help="Description"),
    format: str = typer.Option("json", "--format", "-f", help="Output format"),
):
    """Create a DingTalk todo item."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    async def _run():
        provider = DingTalkProvider()
        return await provider.create_todo(title, description=description)

    result = asyncio.run(_run())
    fmt_output(result, format)


# --- Listen (reverse link) ---

@dingtalk_app.command("listen")
def dingtalk_listen(
    agent: str = typer.Option("claude", "--agent", "-a", help="Default coding agent"),
    work_dir: str = typer.Option(".", "--work-dir", "-w", help="Working directory for agent"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Start DingTalk stream listener (reverse link: IM → Agent)."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    from codingagentim.core.dispatcher import AgentDispatcher
    from codingagentim.providers.dingtalk import DingTalkProvider
    from codingagentim.providers.dingtalk.listener import DingTalkListener

    provider = DingTalkProvider()
    dispatcher = AgentDispatcher(default_agent=agent, work_dir=work_dir)
    listener = DingTalkListener(provider, dispatcher)

    console.print(f"[bold green]Starting DingTalk listener[/bold green]")
    console.print(f"  Agent: {agent}")
    console.print(f"  Work dir: {work_dir}")
    console.print(f"  Press Ctrl+C to stop\n")

    try:
        listener.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Listener stopped[/yellow]")


@dingtalk_app.command("bridge")
def dingtalk_bridge(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Start DingTalk bridge mode (messages → inbox.json, outbox.json → DingTalk)."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    from codingagentim.providers.dingtalk import DingTalkProvider
    from codingagentim.providers.dingtalk.listener import DingTalkListener

    provider = DingTalkProvider()
    listener = DingTalkListener(provider)

    console.print("[bold green]Starting DingTalk bridge[/bold green]")
    console.print("  Mode: inbox/outbox (messages processed by current Claude Code session)")
    console.print("  Press Ctrl+C to stop\n")

    try:
        listener.start_bridge()
    except KeyboardInterrupt:
        console.print("\n[yellow]Bridge stopped[/yellow]")


# --- Inbox commands ---

inbox_app = typer.Typer(name="inbox", help="Inbox queue management (bridge mode)", no_args_is_help=True)
app.add_typer(inbox_app, name="inbox")


@inbox_app.command("check")
def inbox_check(
    format: str = typer.Option("raw", "--format", "-f", help="Output format: raw/json"),
):
    """Check pending messages in inbox (for bridge mode polling)."""
    from codingagentim.core.message_queue import pending_count, _load, INBOX_FILE

    items = _load(INBOX_FILE)
    pending = [i for i in items if i["status"] == "pending"]

    if format == "json":
        fmt_output({"pending_count": len(pending), "messages": pending}, "json")
        return

    if not pending:
        console.print("[dim]No pending messages[/dim]")
        return

    for msg in pending:
        sender = msg.get("sender", "unknown")
        text = msg.get("text", "")[:60]
        console.print(f"[cyan]#{msg['id']}[/cyan] from [bold]{sender}[/bold]: {text}")
    console.print(f"\n[bold]{len(pending)}[/bold] pending message(s)")


@inbox_app.command("pop")
def inbox_pop(
    format: str = typer.Option("json", "--format", "-f", help="Output format"),
):
    """Pop the next pending message from inbox."""
    from codingagentim.core.message_queue import pop_inbox

    msg = pop_inbox()
    if msg:
        fmt_output(msg, format)
    else:
        console.print("[dim]No pending messages[/dim]")


@inbox_app.command("done")
def inbox_done(
    msg_id: str = typer.Argument(..., help="Message ID to mark as done"),
    result: str = typer.Option("", "--result", "-r", help="Result text to write to outbox"),
    format: str = typer.Option("raw", "--format", "-f", help="Output format"),
):
    """Mark an inbox message as done and optionally write result to outbox."""
    from codingagentim.core.message_queue import (
        complete_inbox,
        push_outbox,
        _load,
        INBOX_FILE,
    )

    items = _load(INBOX_FILE)
    original = next((i for i in items if i["id"] == msg_id), None)
    if not original:
        console.print(f"[red]Message not found: {msg_id}[/red]")
        raise typer.Exit(1)

    complete_inbox(msg_id)

    if result:
        outbox_msg = push_outbox(
            inbox_id=msg_id,
            result=result,
            conversation_id=original.get("conversation_id", ""),
            is_group=original.get("is_group", True),
            sender_id=original.get("sender_id", ""),
        )
        console.print(f"[green]Done #{msg_id} → outbox #{outbox_msg['id']}[/green]")
    else:
        console.print(f"[green]Done #{msg_id}[/green]")


# --- Hook commands ---

hook_app = typer.Typer(name="hook", help="Hook integration", no_args_is_help=True)
app.add_typer(hook_app, name="hook")


@hook_app.command("notify")
def hook_notify(
    source_tool: str = typer.Argument(..., help="Source tool (claude-code, codex, gemini)"),
    event_type: str = typer.Argument("task_complete", help="Event type"),
):
    """Send a hook notification to IM."""
    from codingagentim.hooks.notify import run_notify

    run_notify(source_tool, event_type)


# --- Auth commands ---

auth_app = typer.Typer(name="auth", help="Authentication management", no_args_is_help=True)
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login(
    provider: str = typer.Argument(..., help="Provider name (dingtalk)"),
):
    """Configure credentials for an IM provider."""
    if provider == "dingtalk":
        app_key = typer.prompt("DingTalk App Key")
        app_secret = typer.prompt("DingTalk App Secret", hide_input=True)
        robot_code = typer.prompt("Robot Code (optional, press Enter to skip)", default="")

        cfg = config.load_config()
        cfg.setdefault("dingtalk", {})
        cfg["dingtalk"]["app_key"] = app_key
        cfg["dingtalk"]["app_secret"] = app_secret
        if robot_code:
            cfg["dingtalk"]["robot_code"] = robot_code
        config.save_config(cfg)
        console.print(f"[green]DingTalk credentials saved to {config.CONFIG_FILE}[/green]")
    else:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        raise typer.Exit(1)


@auth_app.command("status")
def auth_status():
    """Show current authentication status."""
    cfg = config.load_config()
    dt = cfg.get("dingtalk", {})
    has_key = bool(dt.get("app_key"))
    has_secret = bool(dt.get("app_secret"))
    status = "[green]configured[/green]" if (has_key and has_secret) else "[red]not configured[/red]"
    console.print(f"DingTalk: {status}")


# --- MCP commands ---

mcp_app = typer.Typer(name="mcp", help="MCP server", no_args_is_help=True)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("serve")
def mcp_serve():
    """Start MCP server (stdio transport) for AI tool integration."""
    from codingagentim.mcp_server import run_mcp_server

    run_mcp_server()


# --- Task commands ---

task_app = typer.Typer(name="task", help="Task management", no_args_is_help=True)
app.add_typer(task_app, name="task")


@task_app.command("list")
def task_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter: running/completed/failed"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
):
    """List dispatched agent tasks."""
    from codingagentim.core.task_store import list_tasks

    tasks = list_tasks(status=status, limit=limit)
    if not tasks:
        console.print("[dim]No tasks found[/dim]")
        return

    if format == "json":
        fmt_output([t.model_dump(mode="json") for t in tasks], "json")
        return

    from rich.table import Table

    table = Table(title="Agent Tasks")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Status", width=10)
    table.add_column("Agent", width=8)
    table.add_column("Sender", width=12)
    table.add_column("Prompt", max_width=30)
    table.add_column("Started", width=19)
    table.add_column("Duration", width=10)

    for t in reversed(tasks):
        status_style = {"running": "yellow", "completed": "green", "failed": "red"}.get(t.status, "dim")
        duration = ""
        if t.start_time and t.end_time:
            delta = t.end_time - t.start_time
            duration = f"{delta.total_seconds():.1f}s"
        elif t.start_time and t.status == "running":
            duration = "..."

        started = t.start_time.strftime("%Y-%m-%d %H:%M:%S") if t.start_time else ""
        table.add_row(
            t.id,
            f"[{status_style}]{t.status}[/{status_style}]",
            t.agent,
            t.sender[:12],
            t.prompt[:30],
            started,
            duration,
        )
    console.print(table)


@task_app.command("show")
def task_show(
    task_id: str = typer.Argument(..., help="Task ID"),
    format: str = typer.Option("raw", "--format", "-f", help="Output format"),
):
    """Show task details."""
    from codingagentim.core.task_store import get_task

    task = get_task(task_id)
    if not task:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise typer.Exit(1)

    if format == "json":
        fmt_output(task.model_dump(mode="json"), "json")
        return

    status_style = {"running": "yellow", "completed": "green", "failed": "red"}.get(task.status, "dim")
    console.print(f"[bold]Task {task.id}[/bold]  [{status_style}]{task.status}[/{status_style}]")
    console.print(f"  Agent:    {task.agent}")
    console.print(f"  Sender:   {task.sender}")
    console.print(f"  Prompt:   {task.prompt}")
    if task.start_time:
        console.print(f"  Started:  {task.start_time}")
    if task.end_time:
        console.print(f"  Ended:    {task.end_time}")
    console.print(f"  Exit:     {task.exit_code}")
    if task.summary:
        console.print(f"\n[bold]Summary:[/bold]\n{task.summary}")


@task_app.command("clean")
def task_clean():
    """Remove completed and failed tasks."""
    from codingagentim.core.task_store import clean_tasks

    removed = clean_tasks()
    console.print(f"[green]Cleaned {removed} task(s)[/green]")


# --- Top-level commands ---

@app.command("schema")
def schema():
    """List all providers and their capabilities."""
    import codingagentim.providers.dingtalk  # noqa: F401

    from codingagentim.core.registry import list_providers

    for name, cls in list_providers().items():
        instance = cls()
        fmt_output(instance.get_schema(), "json")


@app.command("version")
def version():
    """Show version."""
    console.print(f"codingagentim {__version__}")


@app.callback()
def main():
    """CodingAgentIM — IM x AI Coding Agent bidirectional bridge."""
    pass
