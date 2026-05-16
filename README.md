# CodingAgentIM

IM x AI Coding Agent bidirectional bridge. Connect DingTalk (and more) with AI coding agents like Claude Code, Codex, Gemini CLI.

## Features

- **Forward link (Agent → IM)**: Coding agents notify IM after task completion via hooks
- **Reverse link (IM → Agent)**: @robot in DingTalk to dispatch tasks to coding agents
- **Bridge mode**: DingTalk messages processed by Claude Code with full project context, supporting continuous conversations per user/group
- **Daemon**: launchd-based auto-start and crash recovery, zero maintenance
- **CLI + MCP Server**: Use from terminal or integrate as MCP tool in IDEs
- **Plugin architecture**: Easy to add new IM providers (DingTalk, Feishu, WeCom...)

## Quick Start

```bash
pip install -e .
codingagentim init
```

`init` does three things:
1. Configures DingTalk credentials (interactive)
2. Creates `CLAUDE.md` with bridge monitoring instructions
3. Installs the bridge daemon (auto-start on login, auto-restart on crash)

That's it. Send a message to the DingTalk robot, and it will be processed by Claude Code.

## Architecture

```
钉钉群/单聊 ──stream──▶ Bridge Daemon (launchd)
                              │
                        fork claude session
                              │
                     Claude Code (full context)
                              │
                        reply to DingTalk
```

The bridge maintains per-user/group conversation sessions, so follow-up messages continue the same Claude Code context.

## Bridge Mode

The bridge connects DingTalk to Claude Code. Two modes:

| Mode | How it works | Pros |
|------|-------------|------|
| `cli` (default) | Spawns `claude --resume --fork-session` subprocess | Full project context, tool use |
| `api` | Direct Anthropic API call | Faster response, no CLI overhead |

### Daemon Management

```bash
codingagentim daemon install         # Install + start (default: cli mode)
codingagentim daemon install --mode api  # API mode
codingagentim daemon status          # Check status
codingagentim daemon restart         # Restart
codingagentim daemon logs            # Tail logs
codingagentim daemon uninstall       # Stop and remove
```

The daemon uses macOS launchd:
- `RunAtLoad` — starts on login
- `KeepAlive` — restarts on crash (10s throttle)
- Logs: `~/.codingagentim/bridge.{out,err}.log`

### Claude Code Integration

After `codingagentim init`, the generated `CLAUDE.md` instructs Claude Code to:
- Monitor bridge activity in real-time via `tail -f`
- Display DingTalk messages as they arrive in the current session

## Forward: Agent → IM

```bash
# Send a message to DingTalk group
codingagentim dingtalk chat send --to "conversation_id" --text "Deploy complete"

# Send to a user
codingagentim dingtalk chat send --to "user_id" --text "PR merged" --user

# Create a todo
codingagentim dingtalk todo create --title "Review PR #42"
```

## Reverse: IM → Agent

```bash
# Start listener (DingTalk @robot → coding agent dispatcher)
codingagentim dingtalk listen --agent claude --work-dir /path/to/repo
```

Then @robot in DingTalk group: `@bot refactor the auth module`

## MCP Server

```bash
codingagentim mcp serve  # stdio transport for IDE integration
```

## Hook Integration

```bash
codingagentim hook notify claude-code task_complete
```

## CLI Reference

```
codingagentim init                  # One-command setup
codingagentim daemon <cmd>          # Daemon management
codingagentim dingtalk bridge       # Start bridge (foreground)
codingagentim dingtalk listen       # Start dispatcher listener
codingagentim dingtalk chat send    # Send message
codingagentim dingtalk contact search  # Search contacts
codingagentim dingtalk calendar list   # List calendar events
codingagentim dingtalk todo create  # Create todo
codingagentim inbox check|pop|done  # Message queue management
codingagentim task list|show|clean  # Task management
codingagentim auth login|status     # Credential management
codingagentim mcp serve             # MCP server
codingagentim hook notify           # Hook notification
codingagentim schema                # Show provider capabilities
codingagentim version               # Show version
```

## Configuration

Config file: `~/.codingagentim/config.toml`

```toml
default_provider = "dingtalk"
default_agent = "claude"

[dingtalk]
app_key = "your_app_key"
app_secret = "your_app_secret"
robot_code = "your_robot_code"

[hook]
notify_target = "your_group_conversation_id"
```

## License

Apache-2.0
