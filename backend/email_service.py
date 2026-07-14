"""
Email service using Microsoft Graph API (application permissions, client
credentials OAuth2 flow) to send transactional emails: password resets,
booking confirmations, meet & greet reminders, vaccination expiry
reminders, and similar notifications.
"""
import os
import time
import httpx

MS_GRAPH_TENANT_ID = os.environ.get("MS_GRAPH_TENANT_ID")
MS_GRAPH_CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID")
MS_GRAPH_CLIENT_SECRET = os.environ.get("MS_GRAPH_CLIENT_SECRET")
MS_GRAPH_SENDER_EMAIL = os.environ.get("MS_GRAPH_SENDER_EMAIL")

_token_cache = {"access_token": None, "expires_at": 0}


def is_configured() -> bool:
    return all([MS_GRAPH_TENANT_ID, MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET, MS_GRAPH_SENDER_EMAIL])


async def _get_access_token() -> str:
    """Fetch (and cache) an OAuth2 access token via the client credentials flow."""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    if not is_configured():
        raise RuntimeError("Microsoft Graph email is not configured")

    url = f"https://login.microsoftonline.com/{MS_GRAPH_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": MS_GRAPH_CLIENT_ID,
        "client_secret": MS_GRAPH_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, data=data)
        if resp.status_code >= 400:
            raise RuntimeError(f"Token request failed: {resp.status_code} {resp.text}")
        payload = resp.json()

    _token_cache["access_token"] = payload["access_token"]
    _token_cache["expires_at"] = now + payload.get("expires_in", 3600)
    return _token_cache["access_token"]


async def send_email(to_email: str, subject: str, html_body: str) -> None:
    """Send an email via Microsoft Graph API. Raises on failure so callers
    can decide how to handle it (e.g. log-and-continue for a booking
    confirmation vs. surfacing an error for a password reset request)."""
    if not is_configured():
        raise RuntimeError("Microsoft Graph email is not configured")

    token = await _get_access_token()
    url = f"https://graph.microsoft.com/v1.0/users/{MS_GRAPH_SENDER_EMAIL}/sendMail"
    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": "true",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            json=message,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Graph sendMail failed: {resp.status_code} {resp.text}")
