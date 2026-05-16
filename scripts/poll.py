#!/usr/bin/env python3
"""Poll DingTalk notifications — short wrapper for cleaner CLI display."""
import asyncio, json, sys
from codingagentim.mcp_server import _poll_notifications

timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 55
interval = int(sys.argv[2]) if len(sys.argv) > 2 else 1

notifs = asyncio.run(_poll_notifications(timeout=timeout, interval=interval))
if notifs:
    for n in notifs:
        print(json.dumps(n, ensure_ascii=False))
