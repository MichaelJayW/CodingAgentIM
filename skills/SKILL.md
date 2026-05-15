# CodingAgentIM Skill

You have access to CodingAgentIM (`codingagentim`) — a CLI tool that bridges IM platforms (DingTalk, etc.) with AI coding agents. Use it to send messages, search contacts, manage todos, query calendars, and receive task dispatches from IM.

## Available Commands

### Send a message to a DingTalk group
```bash
codingagentim dingtalk chat send --to "<conversation_id>" --text "message content"
```

Send markdown:
```bash
codingagentim dingtalk chat send --to "<conversation_id>" --text "**bold** text" --type markdown
```

Send to a specific user (instead of group):
```bash
codingagentim dingtalk chat send --to "<user_id>" --text "hello" --user
```

### Search contacts
```bash
codingagentim dingtalk contact search --query "name or keyword" --limit 10
```

### Create a todo
```bash
codingagentim dingtalk todo create --title "Review PR #42" --desc "Check auth changes"
```

### List calendar events
```bash
codingagentim dingtalk calendar list
codingagentim dingtalk calendar list --date 2026-05-15
```

### Hook notification (called automatically by hooks)
```bash
codingagentim hook notify claude-code task_complete
codingagentim hook notify codex task_complete
```

### List provider capabilities
```bash
codingagentim schema
```

## Output Formats

All commands support `--format` (`-f`) with values: `json`, `table`, `raw`. Default is `json` for send/create, `table` for search/list.

```bash
codingagentim dingtalk contact search -q "alice" -f json
```

## MCP Server Mode

CodingAgentIM can run as an MCP server for IDE integration:
```bash
codingagentim mcp serve
```

This exposes tools: `dingtalk_send_message`, `dingtalk_search_contact`, `dingtalk_create_todo`, `dingtalk_list_calendar`.

## When to Use

- **After completing a task**: Send a summary to the team's DingTalk group.
- **Before starting work**: Check the team calendar for conflicts or search contacts for reviewers.
- **Task tracking**: Create DingTalk todos for follow-up items.
- **Team communication**: Notify about deploys, PR status, or blocking issues.

## Configuration

Credentials are stored in `~/.codingagentim/config.toml`. Run `codingagentim auth login dingtalk` to set up.

## References

- [DingTalk product reference](references/products/dingtalk.md)
