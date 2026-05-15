# CodingAgentIM

IM x AI Coding Agent bidirectional bridge. Connect DingTalk (and more) with AI coding agents like Claude Code, Codex, Gemini CLI.

## Features

- **Forward link (Agent → IM)**: Coding agents notify IM after task completion via hooks
- **Reverse link (IM → Agent)**: @robot in DingTalk to dispatch tasks to coding agents
- **CLI + MCP Server**: Use from terminal or integrate as MCP tool in IDEs
- **Plugin architecture**: Easy to add new IM providers (DingTalk, Feishu, WeCom...)

## Quick Start

```bash
pip install -e .
codingagentim auth login dingtalk
```

### Forward: Agent → IM

```bash
# Send a message to DingTalk group
codingagentim dingtalk chat send --to "conversation_id" --text "Deploy complete"

# Create a todo
codingagentim dingtalk todo create --title "Review PR #42"
```

### Reverse: IM → Agent

```bash
# Start listener (DingTalk @robot → coding agent)
codingagentim dingtalk listen --agent claude --work-dir /path/to/repo
```

Then @robot in DingTalk group: `@bot refactor the auth module`

### MCP Server

```bash
codingagentim mcp serve  # stdio transport for IDE integration
```

### Hook Integration

```bash
codingagentim hook notify claude-code task_complete
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
