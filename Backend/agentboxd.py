
import os
import requests

BASE_URL = "https://api.agentboxd.com/v1"

def get_config():
    return (
        os.environ["AGENTBOXD_API_KEY"],
        os.environ["AGENTBOXD_INBOX_ID"]
    )

def get_emails():
    api_key, inbox_id = get_config()

    response = requests.get(
        f"{BASE_URL}/inboxes/{inbox_id}/messages",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"direction": "inbound", "limit": 20},
        timeout=20
    )
    response.raise_for_status()
    return response.json()["data"]


def reply_to_email(message_id: str, reply_text: str):
    api_key, inbox_id = get_config()

    response = requests.post(
        f"{BASE_URL}/inboxes/{inbox_id}/messages/{message_id}/reply",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"text": reply_text},
        timeout=20
    )
    response.raise_for_status()
    return response.json()
