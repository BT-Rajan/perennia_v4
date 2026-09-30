"""
Thin, provider-abstracted client for outbound WhatsApp messages.
Mirrors llm_client.py's shape: plain httpx calls, no vendor SDK, every
provider detail comes from notifications.* settings.
"""
from __future__ import annotations

import httpx

TWILIO_URL_TEMPLATE = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
META_URL_TEMPLATE = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"

REQUEST_TIMEOUT_SECONDS = 15.0


class WhatsAppError(Exception):
    """Raised for any failure sending a WhatsApp message. Callers treat
    this as best-effort and never let it fail the request that
    triggered the notification (a booking, a cancellation, ...)."""


def _send_twilio(*, account_id: str, api_key: str, from_number: str, to_number: str, message: str) -> None:
    if not from_number:
        raise WhatsAppError("Twilio requires notifications.whatsapp_from_number to be set")
    try:
        resp = httpx.post(
            TWILIO_URL_TEMPLATE.format(account_sid=account_id),
            auth=(account_id, api_key),
            data={"From": f"whatsapp:{from_number}", "To": f"whatsapp:{to_number}", "Body": message},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise WhatsAppError(f"Twilio API returned {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise WhatsAppError(f"Twilio API request failed: {e}") from e


def _send_meta_cloud(*, account_id: str, api_key: str, to_number: str, message: str, **_ignored) -> None:
    try:
        resp = httpx.post(
            META_URL_TEMPLATE.format(phone_number_id=account_id),
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json={"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": message}},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise WhatsAppError(f"Meta Cloud API returned {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise WhatsAppError(f"Meta Cloud API request failed: {e}") from e


_PROVIDERS = {"twilio": _send_twilio, "meta_cloud": _send_meta_cloud}


def send_message(*, provider: str, account_id: str, api_key: str, from_number: str, to_number: str, message: str) -> None:
    if provider not in _PROVIDERS:
        raise WhatsAppError(f"Unsupported or unconfigured provider: {provider!r}")
    if not account_id or not api_key:
        raise WhatsAppError("WhatsApp account ID and API key must both be configured")
    if not to_number:
        raise WhatsAppError("No recipient phone number")
    _PROVIDERS[provider](
        account_id=account_id, api_key=api_key, from_number=from_number, to_number=to_number, message=message,
    )
