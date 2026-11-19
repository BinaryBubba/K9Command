"""
Editable email templates. Every automated email has a built-in default (below).
An admin can customize one in Settings; the customized copy is stored in
email_templates and used instead. Deleting a customized system template resets
it to the default. Admins can also create custom templates and send them by
hand to a household.

Templates use {{placeholders}}. Plain-text values are HTML-escaped when filled
in; the names in html_vars are inserted as-is (buttons, lists, photos).
"""
import re
import html as _html
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import require_role
from db_models import User as UserORM, UserRole

router = APIRouter(prefix="/api/email-templates", tags=["email-templates"])

PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
HS = "font-weight:bold;color:#179D4C;margin:20px 0 6px 0;"
UL = '<ul style="padding-left:20px;margin:6px 0;">'

DEFAULTS = {
    "email_verification": {
        "name": "Email verification",
        "description": "Sent when someone creates an account, or asks for a new verification link.",
        "subject": "Please verify your email address",
        "variables": ["first_name", "verify_link", "verify_button"],
        "html_vars": ["verify_button"],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Welcome to K9 Country Club! Please confirm your email address so we can keep you posted about your pup's visits.</p>"
            "<p>{{verify_button}}</p>"
            "<p>This link expires in 48 hours.</p>"
        ),
    },
    "password_reset": {
        "name": "Password reset",
        "description": "Sent when someone asks to reset their password.",
        "subject": "Reset your K9 Country Club password",
        "variables": ["first_name", "reset_link", "reset_button"],
        "html_vars": ["reset_button"],
        "body": (
            "<p>Hi {{first_name}},</p>"
            "<p>We got a request to reset your K9 Country Club password. This link is good for 1 hour:</p>"
            "<p>{{reset_button}}</p>"
            "<p>If you didn't ask for this, no worries. You can safely ignore this email.</p>"
        ),
    },
    "mag_confirmed": {
        "name": "Meet & Greet confirmed",
        "description": "Sent when a Meet & Greet is confirmed by staff.",
        "subject": "Your Meet & Greet is Confirmed!",
        "variables": ["first_name", "dog_name", "when"],
        "html_vars": [],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Great news! {{dog_name}}'s Meet &amp; Greet is confirmed for <strong>{{when}}</strong>.</p>"
            "<p>We can't wait to meet you both!</p>"
        ),
    },
    "mag_reminder": {
        "name": "Meet & Greet reminder",
        "description": "Sent the day before a confirmed Meet & Greet.",
        "subject": "Reminder: Your Meet & Greet is Coming Up!",
        "variables": ["first_name", "dog_name", "when"],
        "html_vars": [],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Just a friendly reminder that {{dog_name}}'s Meet &amp; Greet is coming up on <strong>{{when}}</strong>.</p>"
            "<p>We can't wait to see you!</p>"
        ),
    },
    "welcome_pass": {
        "name": "Welcome (Meet & Greet passed)",
        "description": "Sent once when a dog passes their Meet & Greet. {{rates}} is built from Settings > Pricing.",
        "subject": "{{dog_name}} passed their Meet & Greet!",
        "variables": ["first_name", "dog_name", "rates", "intake_button", "upload_button"],
        "html_vars": ["rates", "intake_button", "upload_button"],
        "body": (
            "<p><strong>Hi {{first_name}}! We heard you enjoyed your visit today!</strong> {{dog_name}} passed their "
            "Meet &amp; Greet and is all set to stay with us. We wanted to make sure you have everything to make "
            "your pup's stay as easy as possible.</p>"
            '<p style="' + HS + '">First, here\'s what to bring:</p>'
            + UL + "<li>Food packed in individual containers by meal (we suggest ziplocks)</li>"
            "<li>A blanket or bed topper (we supply raised beds in each room)</li>"
            "<li>A safety collar (just a standard collar is fine)</li></ul>"
            '<p style="' + HS + '">Our Pick-Up/Drop-Off Windows:</p>'
            + UL + "<li>8am \u2013 10am</li><li>12pm \u2013 2pm</li><li>4pm \u2013 6pm</li></ul>"
            "<p>We follow this schedule every day of the week!</p>"
            '<p style="' + HS + '">Our Services &amp; Add-Ons</p>'
            "{{rates}}"
            "<p><em>If you're ever unsure what's best for your pup, just ask. We're happy to help customize their stay!</em></p>"
            '<p style="' + HS + '">Help us help you!</p>'
            "<p>Please complete our Doggo Intake Form and upload your pup's vaccination records.</p>"
            "{{intake_button}}<br />{{upload_button}}"
            "<p>We can't wait to see you again!</p>"
        ),
    },
    "mag_conditional": {
        "name": "Thanks for the visit (conditional M&G)",
        "description": "Sent when a Meet & Greet ends with a conditional outcome. Staff conditions are not included.",
        "subject": "Thanks for bringing {{dog_name}} in",
        "variables": ["first_name", "dog_name"],
        "html_vars": [],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Thank you for bringing <strong>{{dog_name}}</strong> in for their Meet &amp; Greet. We loved meeting them, "
            "and we'll be reaching out shortly to talk through next steps for their stays.</p>"
            "<p>If you have any questions in the meantime, just reply to this email or give us a call.</p>"
        ),
    },
    "booking_confirmed": {
        "name": "Booking confirmed",
        "description": "Sent when a stay is confirmed.",
        "subject": "Your K9 Country Club Booking is Confirmed!",
        "variables": ["first_name", "dog_list", "check_in", "check_out"],
        "html_vars": [],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Great news! Your reservation for <strong>{{dog_list}}</strong> is confirmed.</p>"
            "<p><strong>Check-in:</strong> {{check_in}}<br /><strong>Check-out:</strong> {{check_out}}</p>"
            "<p>We can't wait to see you!</p>"
        ),
    },
    "booking_reminder": {
        "name": "Stay reminder",
        "description": "Sent about 2 days before a confirmed stay starts.",
        "subject": "Reminder: Your K9 Country Club Stay is Coming Up!",
        "variables": ["first_name", "dog_list", "check_in"],
        "html_vars": [],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Just a friendly reminder that {{dog_list}}'s stay with us starts on <strong>{{check_in}}</strong>.</p>"
            "<p>We can't wait to see you!</p>"
        ),
    },
    "post_stay": {
        "name": "Thanks for staying",
        "description": "Sent after a stay is checked out (once per booking).",
        "subject": "Thanks for staying with us, {{dog_list}}!",
        "variables": ["first_name", "dog_list", "request_button"],
        "html_vars": ["request_button"],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Thank you for trusting us with <strong>{{dog_list}}</strong>. We loved having them, and we hope they're "
            "settling back in at home.</p>"
            "<p>If you have any feedback about the stay, just reply to this email. When you're ready for the next one:</p>"
            "<p>{{request_button}}</p>"
        ),
    },
    "vaccination_expiring": {
        "name": "Vaccination expiring",
        "description": "Sent when a vaccination is about to expire (14-day window).",
        "subject": "{{dog_name}}'s {{vaccine}} vaccine is expiring soon",
        "variables": ["first_name", "dog_name", "vaccine", "expiry_date"],
        "html_vars": [],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Heads up! {{dog_name}}'s {{vaccine}} vaccination expires on <strong>{{expiry_date}}</strong>.</p>"
            "<p>Please send us updated records before your next stay so check-in stays quick and easy.</p>"
        ),
    },
    "daily_update": {
        "name": "Daily update",
        "description": "Sent when staff send a daily update about a dog's stay.",
        "subject": "A new update about your dog!",
        "variables": ["first_name", "notes", "photos"],
        "html_vars": ["notes", "photos"],
        "body": (
            "<p>Hi {{first_name}}!</p>"
            "<p>Here's an update from your pup's stay with us:</p>"
            "{{notes}}{{photos}}"
        ),
    },
}

CUSTOM_VARS = ["first_name", "full_name"]


def _html_vars(key):
    return set(DEFAULTS[key]["html_vars"]) if key in DEFAULTS else set()


def fill(text_in: str, ctx: dict, html_vars=(), escape=True) -> str:
    """Replace {{placeholders}}. Unknown/missing ones become empty."""
    def sub(m):
        k = m.group(1)
        v = ctx.get(k)
        if v is None:
            return ""
        v = str(v)
        if escape and k not in html_vars:
            return _html.escape(v)
        return v
    return PLACEHOLDER.sub(sub, text_in or "")


def fill_template(key: str, subject: str, body: str, ctx: dict):
    hv = _html_vars(key)
    return fill(subject, ctx, hv, escape=False), fill(body, ctx, hv, escape=True)


async def load_template(db: AsyncSession, org_id: str, key: str):
    """(subject, body) for a key: the admin's saved version if there is one,
    otherwise the built-in default. Never raises for a known key."""
    if key not in DEFAULTS:
        raise KeyError(key)
    try:
        row = (await db.execute(text(
            "SELECT subject, body_html FROM email_templates "
            "WHERE organization_id = :org AND key = :key AND is_active = TRUE"
        ), {"org": org_id, "key": key})).first()
        if row:
            return row.subject, row.body_html
    except Exception as e:
        print(f"Could not load email template {key}, using default: {e}")
    return DEFAULTS[key]["subject"], DEFAULTS[key]["body"]


def build_rates_html(groups) -> str:
    """groups: [(category, ["Label: value", ...])] already HTML-escaped."""
    out = []
    for title, items in groups:
        out.append('<p style="margin:14px 0 4px 0;"><strong>' + title + "</strong></p>"
                   + UL + "".join("<li>" + i + "</li>" for i in items) + "</ul>")
    return "".join(out)


def _sample_ctx():
    from email_service import email_button
    return {
        "first_name": "Alex", "full_name": "Alex Smith", "dog_name": "Buddy", "dog_list": "Buddy, Daisy",
        "when": "Saturday, December 5, 2026 (10:00-10:30)", "check_in": "Friday, December 11, 2026",
        "check_out": "Tuesday, December 15, 2026", "vaccine": "Rabies", "expiry_date": "Monday, December 21, 2026",
        "verify_link": "https://k9cmd.maniacranch.com/verify-email?token=sample",
        "reset_link": "https://k9cmd.maniacranch.com/reset-password?token=sample",
        "verify_button": email_button("https://k9cmd.maniacranch.com", "Verify My Email"),
        "reset_button": email_button("https://k9cmd.maniacranch.com", "Reset My Password"),
        "intake_button": email_button("https://k9cmd.maniacranch.com/forms", "Fill Out the Intake Form"),
        "upload_button": email_button("https://k9cmd.maniacranch.com", "Upload Vaccination Records"),
        "request_button": email_button("https://k9cmd.maniacranch.com/customer/request", "Request a Stay"),
        "rates": build_rates_html([("Boarding", ["Nightly Rate: $36", "Holiday Rate: $44"]), ("Daycare", ["Daily Rate: $36"])]),
        "notes": "<p>Buddy had a great day and made a new friend at playgroup!</p>",
        "photos": "",
    }


def _clean(v, field, max_len):
    v = str(v if v is not None else "").strip()
    if not v:
        raise HTTPException(status_code=400, detail=f"{field} cannot be empty")
    if len(v) > max_len:
        raise HTTPException(status_code=400, detail=f"{field} is too long")
    return v


def _is_custom(key):
    return key.startswith("custom_")


@router.get("")
async def list_templates(
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(text(
        "SELECT key, name, subject, body_html, is_system FROM email_templates WHERE organization_id = :org"
    ), {"org": current_user.organization_id})).fetchall()
    saved = {r.key: r for r in rows}
    out = []
    for key, d in DEFAULTS.items():
        r = saved.get(key)
        out.append({
            "key": key, "name": d["name"], "description": d["description"], "is_system": True,
            "is_customized": r is not None,
            "subject": r.subject if r else d["subject"],
            "body_html": r.body_html if r else d["body"],
            "default_subject": d["subject"], "default_body": d["body"],
            "variables": d["variables"],
        })
    for r in rows:
        if _is_custom(r.key):
            out.append({
                "key": r.key, "name": r.name, "description": "Custom template. Send it by hand to a household.",
                "is_system": False, "is_customized": True, "subject": r.subject, "body_html": r.body_html,
                "default_subject": None, "default_body": None, "variables": CUSTOM_VARS,
            })
    return out


@router.post("")
async def create_custom(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    name = _clean(data.get("name"), "name", 120)
    subject = _clean(data.get("subject"), "subject", 200)
    body = _clean(data.get("body_html"), "body_html", 50000)
    key = "custom_" + uuid.uuid4().hex[:10]
    await db.execute(text("""
        INSERT INTO email_templates (id, organization_id, key, name, subject, body_html, is_system)
        VALUES (:id, :org, :key, :name, :subject, :body, FALSE)
    """), {"id": str(uuid.uuid4()), "org": current_user.organization_id, "key": key,
           "name": name, "subject": subject, "body": body})
    await db.commit()
    return {"key": key, "created": True}


@router.post("/preview")
async def preview(
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
):
    from email_service import wrap_email
    key = data.get("key") or ""
    subject, body = fill_template(key, str(data.get("subject") or ""), str(data.get("body_html") or ""), _sample_ctx())
    return {"subject": subject, "html": wrap_email(body)}


@router.put("/{key}")
async def save_template(
    key: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    if key not in DEFAULTS and not _is_custom(key):
        raise HTTPException(status_code=404, detail="Unknown template")
    subject = _clean(data.get("subject"), "subject", 200)
    body = _clean(data.get("body_html"), "body_html", 50000)
    org = current_user.organization_id
    if key in DEFAULTS:
        await db.execute(text("""
            INSERT INTO email_templates (id, organization_id, key, name, subject, body_html, is_system)
            VALUES (:id, :org, :key, :name, :subject, :body, TRUE)
            ON CONFLICT (organization_id, key)
            DO UPDATE SET subject = :subject, body_html = :body, updated_at = now()
        """), {"id": str(uuid.uuid4()), "org": org, "key": key, "name": DEFAULTS[key]["name"],
               "subject": subject, "body": body})
    else:
        params = {"org": org, "key": key, "subject": subject, "body": body}
        sets = "subject = :subject, body_html = :body, updated_at = now()"
        if data.get("name"):
            params["name"] = _clean(data.get("name"), "name", 120)
            sets += ", name = :name"
        res = await db.execute(text(
            f"UPDATE email_templates SET {sets} WHERE organization_id = :org AND key = :key"), params)
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Template not found")
    await db.commit()
    return {"saved": True}


@router.delete("/{key}")
async def delete_or_reset(
    key: str,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """System template: reset to the built-in default. Custom template: delete it."""
    if key not in DEFAULTS and not _is_custom(key):
        raise HTTPException(status_code=404, detail="Unknown template")
    await db.execute(text(
        "DELETE FROM email_templates WHERE organization_id = :org AND key = :key"
    ), {"org": current_user.organization_id, "key": key})
    await db.commit()
    return {"reset" if key in DEFAULTS else "deleted": True}


@router.post("/{key}/send-test")
async def send_test(
    key: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from email_service import send_email, is_configured
    if not is_configured():
        raise HTTPException(status_code=503, detail="Email is not configured")
    subject, body = data.get("subject"), data.get("body_html")
    if not subject or not body:
        if key in DEFAULTS:
            subject, body = await load_template(db, current_user.organization_id, key)
        else:
            raise HTTPException(status_code=400, detail="subject and body_html required")
    subject, body = fill_template(key, subject, body, _sample_ctx())
    await send_email(to_email=current_user.email, subject="[TEST] " + subject, html_body=body)
    return {"sent_to": current_user.email}


@router.post("/{key}/send")
async def send_custom(
    key: str,
    data: dict,
    current_user: UserORM = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Send a custom template by hand to a household's portal accounts."""
    from email_service import send_email, is_configured
    if not _is_custom(key):
        raise HTTPException(status_code=400, detail="Only custom templates can be sent by hand")
    if not is_configured():
        raise HTTPException(status_code=503, detail="Email is not configured")
    household_id = data.get("household_id")
    if not household_id:
        raise HTTPException(status_code=400, detail="household_id required")
    tpl = (await db.execute(text(
        "SELECT subject, body_html FROM email_templates WHERE organization_id = :org AND key = :key"
    ), {"org": current_user.organization_id, "key": key})).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    users = (await db.execute(select(UserORM).where(
        UserORM.household_id == household_id,
        UserORM.organization_id == current_user.organization_id,
        UserORM.role == UserRole.CUSTOMER,
    ))).scalars().all()
    sent = 0
    for u in users:
        if not u.email:
            continue
        first = (u.full_name or "").split(" ")[0] or "there"
        subj, body = fill_template(key, tpl.subject, tpl.body_html, {"first_name": first, "full_name": u.full_name or ""})
        try:
            await send_email(to_email=u.email, subject=subj, html_body=body)
            sent += 1
        except Exception as e:
            print(f"Failed to send custom email to {u.email}: {e}")
    return {"sent": sent}
