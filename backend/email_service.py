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


LOGO_URL = "https://k9cmd.maniacranch.com/email-logo.png"
BRAND_GREEN = "#179D4C"
SOCIAL_LINKS = [
    ("Facebook", "https://www.facebook.com/K9CountryClubKennel"),
    ("Instagram", "https://www.instagram.com/twogoofybrothers/"),
    ("TikTok", "https://www.tiktok.com/@maniacranch"),
    ("YouTube", "https://www.youtube.com/@K9CountryClub"),
]


def email_button(href: str, label: str) -> str:
    """A green call-to-action button, inline-styled so it survives email clients."""
    return (
        f'<a href="{href}" style="display:inline-block;padding:12px 20px;margin:10px 0;'
        f'background-color:{BRAND_GREEN};color:#ffffff;text-decoration:none;'
        f'border-radius:6px;font-weight:bold;">{label}</a>'
    )


def wrap_email(body_html: str) -> str:
    """Put an email body inside the shared K9 Country Club layout."""
    socials = " | ".join(
        f'<a href="{url}" style="color:{BRAND_GREEN};text-decoration:none;">{name}</a>'
        for name, url in SOCIAL_LINKS
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
  a {{ color: {BRAND_GREEN}; }}
</style>
</head>
<body style="margin:0;padding:0;background:#ffffff;">
<div style="max-width:600px;margin:auto;padding:20px;font-family:Arial,sans-serif;color:#333333;font-size:15px;line-height:1.5;">
  <div style="text-align:center;margin-bottom:16px;">
    <img src="{LOGO_URL}" alt="K9 Country Club" width="200" style="max-width:200px;height:auto;" />
  </div>
  {body_html}
  <p style="margin:24px 0 0 0;">Your Friends at<br /><strong style="color:{BRAND_GREEN};">K9 Country Club</strong></p>
  <div style="text-align:center;margin-top:30px;padding-top:16px;border-top:1px solid #eeeeee;font-size:13px;color:#666666;">
    <p style="margin:0 0 6px 0;">Follow us on social media!</p>
    <p style="margin:0;">{socials}</p>
  </div>
</div>
</body>
</html>"""


async def send_email(to_email: str, subject: str, html_body: str, wrap: bool = True) -> None:
    """Send an email via Microsoft Graph API, inside the shared brand layout
    unless wrap=False. Raises on failure so callers can decide how to handle
    it (e.g. log-and-continue for a booking confirmation vs. surfacing an
    error for a password reset request)."""
    if not is_configured():
        raise RuntimeError("Microsoft Graph email is not configured")

    if wrap:
        html_body = wrap_email(html_body)

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
