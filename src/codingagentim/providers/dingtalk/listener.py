"""DingTalk Stream listener — reverse link entry point (IM → Agent)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import dingtalk_stream
from dingtalk_stream import AckMessage
from rich.console import Console

from codingagentim import config
from codingagentim.core.dispatcher import AgentDispatcher
from codingagentim.core.message_queue import (
    complete_outbox,
    pop_outbox,
    push_inbox,
)
from codingagentim.core.models import Message

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider

logger = logging.getLogger(__name__)
console = Console()


class BotMessageHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, provider: DingTalkProvider, dispatcher: AgentDispatcher):
        super().__init__()
        self.provider = provider
        self.dispatcher = dispatcher

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        text = (incoming.text.content or "").strip()

        if not text:
            return AckMessage.STATUS_OK, "OK"

        sender = incoming.sender_nick or ""
        conversation_id = incoming.conversation_id or ""
        is_group = incoming.conversation_type == "2"
        chat_type = "群聊" if is_group else "单聊"

        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {text[:80]}")
        console.print(f"[dim]  Dispatching to {self.dispatcher.default_agent}...[/dim]")
        logger.info("Received %s message from %s: %s", chat_type, sender, text[:100])

        msg = Message(
            sender_id=incoming.sender_staff_id or incoming.sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
        )

        try:
            await self.provider.reply_message(
                msg, f"⏳ 收到「{text[:20]}」，正在处理...", msg_type="markdown",
            )
        except Exception as e:
            logger.warning("Failed to send ack reply: %s", e)

        progress_count = 0

        async def on_progress(line: str) -> None:
            nonlocal progress_count
            progress_count += 1
            snippet = line[:60] + ("..." if len(line) > 60 else "")
            try:
                await self.provider.reply_message(
                    msg, f"🔄 进度 #{progress_count}：{snippet}", msg_type="markdown",
                )
            except Exception as e:
                logger.warning("Failed to send progress: %s", e)

        def on_output(line: str) -> None:
            console.print(f"[dim]│[/dim] {line}", end="", highlight=False)

        result = await self.dispatcher.dispatch(
            text,
            on_output=on_output,
            on_progress=on_progress,
            sender=sender,
            conversation_id=conversation_id,
        )

        status_style = "green" if result.exit_code == 0 else "red"
        console.print(f"[bold {status_style}]━━━ 完成[/bold {status_style}] exit={result.exit_code}")

        reply = self._format_result_markdown(text, result)
        try:
            await self.provider.reply_message(msg, reply, msg_type="markdown")
        except Exception as e:
            logger.error("Failed to send result reply: %s", e)

        return AckMessage.STATUS_OK, "OK"

    @staticmethod
    def _format_result_markdown(prompt: str, result) -> str:
        status = "✅ 完成" if result.exit_code == 0 else "❌ 失败"
        parts = [f"### {status}"]
        parts.append(f"**任务**: {prompt[:50]}")
        parts.append(f"**Agent**: {result.agent}")
        if result.summary:
            parts.append(f"\n{result.summary[:1500]}")
        return "\n\n".join(parts)


class BridgeMessageHandler(dingtalk_stream.ChatbotHandler):
    """Bridge mode: resumes Claude Code session to process messages."""

    def __init__(self, provider: DingTalkProvider, session_id: str = "", work_dir: str = "."):
        super().__init__()
        self.provider = provider
        self.session_id = session_id
        self.work_dir = work_dir

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        text = (incoming.text.content or "").strip()

        if not text:
            return AckMessage.STATUS_OK, "OK"

        sender = incoming.sender_nick or ""
        sender_id = incoming.sender_staff_id or incoming.sender_id or ""
        conversation_id = incoming.conversation_id or ""
        is_group = incoming.conversation_type == "2"
        chat_type = "群聊" if is_group else "单聊"

        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {text[:80]}")
        logger.info("Received %s from %s: %s", chat_type, sender, text[:100])

        msg = Message(
            sender_id=sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
        )

        try:
            await self.provider.reply_message(
                msg, f"⏳ 收到「{text[:20]}」，正在处理...", msg_type="markdown",
            )
        except Exception as e:
            logger.warning("Failed to send ack: %s", e)

        prompt = f"[钉钉消息 from {sender}]: {text}"
        console.print(f"[dim]  → claude --resume {self.session_id[:8]}... -p[/dim]")

        try:
            cmd = ["claude", "--resume", self.session_id, "--fork-session", "-p", prompt, "--output-format", "json"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            import json as _json
            try:
                data = _json.loads(output.strip())
                result_text = data.get("result", output[:1500])
            except (ValueError, _json.JSONDecodeError):
                result_text = output.strip()[:1500] if output.strip() else f"处理完成 (exit {proc.returncode})"

            if proc.returncode != 0 and not result_text:
                result_text = f"执行失败 (exit {proc.returncode})\n{stderr.decode()[:500]}"

            console.print(f"[bold green]━━━ 完成[/bold green] exit={proc.returncode}")
        except FileNotFoundError:
            result_text = "Claude CLI 未找到，请确认已安装"
            console.print(f"[bold red]━━━ 失败[/bold red] claude not found")

        try:
            await self.provider.reply_message(msg, result_text, msg_type="markdown")
        except Exception as e:
            logger.error("Failed to send result: %s", e)

        # Also write to inbox/outbox for history tracking
        push_inbox(text=text, sender=sender, sender_id=sender_id,
                   conversation_id=conversation_id if is_group else "", is_group=is_group)

        return AckMessage.STATUS_OK, "OK"


class DingTalkListener:
    def __init__(
        self,
        provider: DingTalkProvider,
        dispatcher: AgentDispatcher | None = None,
        app_key: str | None = None,
        app_secret: str | None = None,
    ):
        self.provider = provider
        self.dispatcher = dispatcher
        self._app_key = app_key or config.get("dingtalk.app_key", "")
        self._app_secret = app_secret or config.get("dingtalk.app_secret", "")

    def start(self) -> None:
        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = BotMessageHandler(self.provider, self.dispatcher)
        client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk stream listener...")
        client.start_forever()

    def start_bridge(self, session_id: str = "", work_dir: str = ".") -> None:
        """Start in bridge mode: resume Claude Code session to process messages."""
        if not session_id:
            session_id = self._find_latest_session()

        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = BridgeMessageHandler(self.provider, session_id=session_id, work_dir=work_dir)
        client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk bridge (session: %s...)", session_id[:8])
        client.start_forever()

    @staticmethod
    def _find_latest_session() -> str:
        from pathlib import Path
        session_dir = Path.home() / ".claude" / "projects"
        jsonl_files = sorted(session_dir.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
        if jsonl_files:
            return jsonl_files[0].stem
        return ""

    async def _outbox_watcher(self, poll_interval: float = 2.0) -> None:
        """Poll outbox.json and send results back to DingTalk."""
        console.print("[dim]Outbox watcher started[/dim]")
        while True:
            try:
                msg = pop_outbox()
                if msg:
                    console.print(f"[bold green]━━━ 发送回复[/bold green]")
                    try:
                        if msg.get("is_group") and msg.get("conversation_id"):
                            await self.provider.send_message(
                                msg["conversation_id"], msg["result"], msg_type="markdown",
                            )
                        elif msg.get("sender_id"):
                            await self.provider.send_to_user(
                                [msg["sender_id"]], msg["result"], msg_type="markdown",
                            )
                        complete_outbox(msg["id"])
                        console.print(f"[dim]  ✓ sent[/dim]")
                    except Exception as e:
                        logger.error("Failed to send outbox message: %s", e)
                        console.print(f"[red]  ✗ send failed: {e}[/red]")
            except Exception as e:
                logger.error("Outbox watcher error: %s", e)
            await asyncio.sleep(poll_interval)
