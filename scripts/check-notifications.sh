#!/bin/bash
# Check for new DingTalk bridge notifications since last read offset.
# Outputs new JSONL lines (if any), then updates offset file.
NOTIF_FILE="$HOME/.codingagentim/notifications.jsonl"
OFFSET_FILE="$HOME/.codingagentim/.notif_cron_offset"

[ -f "$NOTIF_FILE" ] || exit 0

offset=$(cat "$OFFSET_FILE" 2>/dev/null || echo "0")
size=$(wc -c < "$NOTIF_FILE" | tr -d ' ')

[ "$size" -le "$offset" ] && exit 0

tail -c +"$((offset + 1))" "$NOTIF_FILE"
echo "$size" > "$OFFSET_FILE"
