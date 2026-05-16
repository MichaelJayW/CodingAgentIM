"""DingTalk Stream listener — reverse link entry point (IM → Agent)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import dingtalk_stream

from codingagentim import config
from codingagentim.providers.dingtalk.handlers import (
    APIBridgeMessageHandler,
    BotMessageHandler,
    BridgeMessageHandler,
    InboxMessageHandler,
)

if TYPE_CHECKING:
    from codingagentim.core.dispatcher import AgentDispatcher
    from codingagentim.providers.dingtalk.provider import DingTalkProvider


logger = logging.getLogger(__name__)


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
        self._client = None

    def _setup_signal_handlers(self) -> None:
        import signal

        def _shutdown(signum, frame):
            logger.info("Received signal %s, shutting down gracefully...", signum)
            if self._client:
                try:
                    self._client.stop()
                except Exception:
                    pass
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

    def start(self) -> None:
        self._setup_signal_handlers()
        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = BotMessageHandler(self.provider, self.dispatcher)
        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk stream listener...")
        self._client.start_forever()

    def start_bridge(self, session_id: str = "", work_dir: str = ".") -> None:
        """Start in bridge mode: resume Claude Code session to process messages."""
        self._setup_signal_handlers()
        if not session_id:
            session_id = self._find_latest_session()

        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = BridgeMessageHandler(self.provider, session_id=session_id, work_dir=work_dir)
        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk bridge (session: %s...)", session_id[:8])
        self._client.start_forever()

    def start_inbox(self) -> None:
        """Start in inbox mode: queue messages for the active Claude session."""
        self._setup_signal_handlers()
        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = InboxMessageHandler(self.provider)
        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk inbox mode (messages queued for active session)")
        self._client.start_forever()

    def start_api(self, model: str = "", system_prompt: str = "") -> None:
        """Start in direct API mode: fastest response using Anthropic SDK."""
        self._setup_signal_handlers()
        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = APIBridgeMessageHandler(self.provider, model=model, system_prompt=system_prompt)
        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk API mode (model: %s)", model or "env default")
        self._client.start_forever()

    @staticmethod
    def _find_latest_session() -> str:
        session_dir = Path.home() / ".claude" / "projects"
        jsonl_files = sorted(session_dir.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
        if jsonl_files:
            return jsonl_files[0].stem
        return ""
