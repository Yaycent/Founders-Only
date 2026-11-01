"""Agentboxd inbox access restored from the previous project implementation."""

from __future__ import annotations

import os
from datetime import datetime
from email.utils import parseaddr

import requests


BASE_URL = "https://api.agentboxd.com/v1"


class AgentboxdConfigurationError(RuntimeError):
    """Raised when the Agentboxd credentials are not configured."""


def get_config() -> tuple[str, str]:
    api_key = os.environ.get("AGENTBOXD_API_KEY", "").strip()
    inbox_id = os.environ.get("AGENTBOXD_INBOX_ID", "").strip()
    if not api_key or not inbox_id:
        raise AgentboxdConfigurationError("Agentboxd is not configured.")
    return api_key, inbox_id


def _request_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def get_messages() -> list[dict]:
    api_key, inbox_id = get_config()
    response = requests.get(
        f"{BASE_URL}/inboxes/{inbox_id}/messages",
        headers=_request_headers(api_key),
        params={"direction": "inbound", "limit": 20},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def _sender_details(message: dict) -> tuple[str, str]:
    sender = message.get("from") or message.get("sender") or message.get("from_email") or "Unknown sender"
    if isinstance(sender, dict):
        email = sender.get("email") or sender.get("address") or ""
        name = sender.get("name") or sender.get("display_name") or email or "Unknown sender"
        return str(name), str(email)
    name, email = parseaddr(str(sender))
    return name or str(sender), email


def _format_date(value) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%b %d, %I:%M %p").replace(" 0", " ")
    except (TypeError, ValueError):
        return str(value)


def normalize_message(message: dict) -> dict:
    name, email = _sender_details(message)
    body = message.get("text") or message.get("body") or message.get("text_body") or message.get("snippet") or ""
    body = str(body)
    subject = str(message.get("subject") or "(No subject)")
    return {
        "id": str(message.get("id") or message.get("_id") or ""),
        "name": name,
        "email": email,
        "subject": subject,
        "preview": str(message.get("preview") or message.get("snippet") or body[:150]),
        "date": _format_date(message.get("received_at") or message.get("created_at") or message.get("date")),
        "category": str(message.get("category") or "Others"),
        "priority": str(message.get("priority") or "Normal").title(),
        "unread": bool(message.get("unread", not message.get("is_read", False))),
        "important": bool(message.get("important", False)),
        "body": body,
    }


def get_emails() -> list[dict]:
    return [normalize_message(message) for message in get_messages()]


def reply_to_email(message_id: str, reply_text: str) -> dict:
    api_key, inbox_id = get_config()
    response = requests.post(
        f"{BASE_URL}/inboxes/{inbox_id}/messages/{message_id}/reply",
        headers=_request_headers(api_key),
        json={"text": reply_text},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
