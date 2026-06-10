from __future__ import annotations

import logging
import os
from threading import Event

from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from .config import ConfigStore, set_slack_channel
from .monitor import ApartmentMonitor
from .notifier import SlackNotifier
from .slack_commands import CommandResult, SlackCommandProcessor

logger = logging.getLogger(__name__)


class ApartmentSlackApp:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self.web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        self.client = SocketModeClient(
            app_token=os.environ["SLACK_APP_TOKEN"],
            web_client=self.web_client,
        )
        self.processor = SlackCommandProcessor(config_store)
        self.client.socket_mode_request_listeners.append(self._handle_socket_request)

    def start(self, *, block: bool = True) -> None:
        self.client.connect()
        logger.info("Apartment Slack bot connected")
        if block:
            Event().wait()

    def _handle_socket_request(self, client: SocketModeClient, request: SocketModeRequest) -> None:
        if request.type != "events_api":
            return
        client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
        event = request.payload.get("event", {})
        event_type = event.get("type")
        if event_type not in {"message", "app_mention"}:
            return
        if event.get("bot_id") or event.get("subtype"):
            return
        text = event.get("text", "").strip()
        channel = event.get("channel")
        if not text or not channel:
            return
        if event_type == "message" and not text.lower().startswith("apt "):
            return

        try:
            result = self._handle_text(text, channel)
        except Exception as exc:
            logger.exception("Slack command failed")
            self.web_client.chat_postMessage(channel=channel, text=f"Apartment command failed: {exc}")
            return

        self.web_client.chat_postMessage(channel=channel, text=result.message)
        if result.run_now:
            config = self.config_store.load()
            notifier = SlackNotifier(channel_id=config.slack_channel_id or channel)
            fresh = ApartmentMonitor(self.config_store, notifier=notifier).run_once()
            if not fresh:
                self.web_client.chat_postMessage(channel=channel, text="No new matching apartments found.")

    def _handle_text(self, text: str, channel: str):
        normalized = text.strip()
        if normalized.startswith("<@") and ">" in normalized:
            normalized = normalized.split(">", 1)[1].strip()
        if normalized.startswith("apt "):
            normalized = normalized[4:].strip()
        if normalized == "bind here":
            config = self.config_store.load()
            self.config_store.save(set_slack_channel(config, channel))
            return CommandResult(f"Apartment notifications bound to <#{channel}>.")
        return self.processor.handle(text)
