"""BridgeMessageHandler — resumes Claude Code sessions to process messages."""

from __future__ import annotations

import asyncio
import json as _json
from typing import TYPE_CHECKING

import dingtalk_stream
from dingtalk_stream import AckMessage

from codingagentim.core.models import Message
from codingagentim.providers.dingtalk.handlers.base import (
    DeduplicatedHandler,
    console,
    find_claude_bin,
    load_sessions,
    logger,
    push_notification,
    save_sessions,
)

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider


class BridgeMessageHandler(DeduplicatedHandler, dingtalk_stream.ChatbotHandler):
    """Bridge mode: resumes Claude Code session to process messages."""

    def __init__(self, provider: DingTalkProvider, session_id: str = "", work_dir: str = "."):
        DeduplicatedHandler.__init__(self)
        dingtalk_stream.ChatbotHandler.__init__(self)
        self.provider = provider
        self.session_id = session_id
        self.work_dir = work_dir
        self._user_sessions: dict[str, str] = load_sessions()

    def _persist_sessions(self) -> None:
        save_sessions(self._user_sessions)

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        if self._is_duplicate(incoming.message_id):
            return AckMessage.STATUS_OK, "OK"
        text = (incoming.text.content or "").strip()

        if not text:
            return AckMessage.STATUS_OK, "OK"

        sender = incoming.sender_nick or ""
        sender_id = incoming.sender_staff_id or incoming.sender_id or ""
        conversation_id = incoming.conversation_id or ""
        is_group = incoming.conversation_type == "2"
        chat_type = "群聊" if is_group else "单聊"
        user_key = conversation_id if is_group else sender_id

        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {text[:80]}")
        logger.info("Received %s from %s: %s", chat_type, sender, text[:100])
        push_notification(sender, text, ntype="received", chat=chat_type)

        msg = Message(
            sender_id=sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
        )

        try:
            await self.provider.reply_message(
                msg, "⏳ [CodingAgentIM] 收到，正在处理...", msg_type="markdown",
            )
        except Exception as e:
            logger.warning("Failed to send ack: %s", e)

        resume_id = self._user_sessions.get(user_key, self.session_id)
        is_followup = user_key in self._user_sessions
        prompt = f"[钉钉{chat_type} from {sender}]: {text}"

        claude_bin = find_claude_bin()
        if is_followup:
            cmd = [claude_bin, "--resume", resume_id, "--permission-mode", "auto",
                   "--verbose", "-p", prompt, "--output-format", "stream-json"]
            console.print(f"[dim]  → 继续对话 {resume_id[:8]}...[/dim]")
        else:
            cmd = [claude_bin, "--resume", self.session_id, "--fork-session",
                   "--permission-mode", "auto", "--verbose", "-p", prompt, "--output-format", "stream-json"]
            console.print(f"[dim]  → 新对话 fork from {self.session_id[:8]}...[/dim]")

        try:
            result_text, new_session_id = await self._run_claude_streaming(cmd, msg)
            if new_session_id:
                self._user_sessions[user_key] = new_session_id
                self._persist_sessions()
            console.print(f"[bold green]━━━ 完成[/bold green]")
            push_notification(sender, text, ntype="completed", chat=chat_type, result=result_text)
        except FileNotFoundError:
            result_text = "Claude CLI 未找到"
            console.print(f"[bold red]━━━ 失败[/bold red]")
            push_notification(sender, text, ntype="failed", chat=chat_type, result=result_text)
        except OSError as e:
            result_text = f"执行异常: {e}"
            console.print(f"[bold red]━━━ 失败[/bold red]")
            logger.error("Subprocess OS error: %s", e)
            push_notification(sender, text, ntype="failed", chat=chat_type, result=result_text)

        try:
            reply = result_text.rstrip() + "\n\n---\n*Powered by CodingAgentIM*"
            await self.provider.reply_message(msg, reply, msg_type="markdown")
        except Exception as e:
            logger.error("Failed to send result: %s", e)

        return AckMessage.STATUS_OK, "OK"

    SUBPROCESS_TIMEOUT = 300  # 5 minutes

    async def _run_claude_streaming(self, cmd: list[str], msg: Message) -> tuple[str, str]:
        """Run claude with stream-json, send progress to DingTalk, return (result, session_id)."""
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=self.work_dir,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )

        result_text = ""
        session_id = ""

        try:
            result_text, session_id = await asyncio.wait_for(
                self._read_claude_output(proc), timeout=self.SUBPROCESS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Claude subprocess timed out after %ds", self.SUBPROCESS_TIMEOUT)
            proc.kill()
            await proc.wait()
            result_text = f"⏰ 执行超时（{self.SUBPROCESS_TIMEOUT}秒），已终止"

        return result_text, session_id

    async def _read_claude_output(self, proc: asyncio.subprocess.Process) -> tuple[str, str]:
        """Read stream-json output from claude subprocess."""
        result_text = ""
        session_id = ""

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            try:
                event = _json.loads(line.decode().strip())
            except (ValueError, _json.JSONDecodeError):
                continue

            etype = event.get("type", "")

            if etype == "system" and event.get("session_id"):
                session_id = event["session_id"]
            elif etype == "result":
                result_text = event.get("result", "")
                if not session_id:
                    session_id = event.get("session_id", "")

        stderr = (await proc.stderr.read()).decode()
        await proc.wait()

        if not result_text and proc.returncode != 0:
            result_text = f"执行失败\n{stderr[:500]}"
        elif not result_text:
            result_text = "处理完成"

        return result_text, session_id
