# -*- coding: utf-8 -*-
import os

from .client import TelegramClient
from .settings import load_settings


def send_text_report(text, title="RAT6 AI Advisor", require_enabled=True):
    settings = load_settings()
    if require_enabled and not settings.get("enabled"):
        return {"ok": False, "skipped": True, "error": "Telegram report is disabled."}
    chat_id = settings.get("report_chat_id")
    if not chat_id:
        return {"ok": False, "error": "Telegram report_chat_id is not configured."}
    client = TelegramClient(token_env=settings.get("bot_token_env", "TELE_BOT_KEY"))
    return client.send_long_message(
        chat_id,
        text,
        chunk_size=settings.get("chunk_size", 3500),
        title=title,
    )


def send_advisor_response(path, title="RAT6 AI Advisor Response"):
    if not path or not os.path.exists(path):
        return {"ok": False, "error": "advisor_response.md not found."}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return send_text_report(text, title=title, require_enabled=True)
