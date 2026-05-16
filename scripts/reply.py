#!/usr/bin/env python3
"""Reply to DingTalk user — short wrapper for cleaner CLI display."""
import asyncio, sys
from codingagentim.providers.dingtalk import DingTalkProvider

sender_id = sys.argv[1]
content = sys.argv[2]
msg_type = sys.argv[3] if len(sys.argv) > 3 else "text"

async def main():
    provider = DingTalkProvider()
    await provider.send_to_user([sender_id], content, msg_type)

asyncio.run(main())
