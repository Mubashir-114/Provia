"""Email transport abstraction for Provia.

Sends mail through the Resend HTTPS API when ``RESEND_API_KEY`` is configured,
otherwise it falls back to Django's configured ``EMAIL_BACKEND`` (e.g. local
Gmail SMTP or the ``locmem`` backend used in tests). This keeps the existing
localhost/Gmail behaviour intact while allowing Render Free (which blocks
outbound SMTP on ports 25/465/587) to deliver mail over HTTPS.

Neither the API key nor any credential is ever logged.
"""
import base64
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(
    to,
    subject,
    *,
    text=None,
    html=None,
    from_email=None,
    attachments=None,
):
    """Send an email through the configured transport.

    ``attachments`` is a list of dicts with keys:
        ``filename`` (str), ``content`` (bytes),
        ``content_id`` (str, optional), ``disposition`` (str, optional).

    Returns ``True`` if the message was handed to a transport, ``False``
    otherwise. Callers must treat ``False`` as non-fatal.
    """
    if isinstance(to, str):
        to = [to]
    if not to:
        return False

    api_key = getattr(settings, "RESEND_API_KEY", "") or ""
    sender = (
        from_email
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or "onboarding@resend.dev"
    )

    if api_key:
        return _send_via_resend(api_key, sender, to, subject, text, html, attachments)
    return _send_via_django(sender, to, subject, text, html, attachments)


def _send_via_django(sender, to, subject, text, html, attachments):
    from django.core.mail import EmailMultiAlternatives
    from email.mime.image import MIMEImage

    email = EmailMultiAlternatives(
        subject=subject,
        body=text or "",
        from_email=sender,
        to=to,
    )
    if html:
        email.attach_alternative(html, "text/html")

    for att in attachments or []:
        content = att["content"]
        content_id = att.get("content_id")
        if content_id:
            img = MIMEImage(content)
            img.add_header("Content-ID", f"<{content_id}>")
            img.add_header("Content-Disposition", att.get("disposition", "inline"))
            email.attach(img)
        else:
            email.attach(att["filename"], content)

    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Failed to send email via Django backend to %s", to)
        return False


def _send_via_resend(api_key, sender, to, subject, text, html, attachments):
    try:
        import resend
    except ImportError:
        logger.error(
            "RESEND_API_KEY is configured but the 'resend' package is not installed."
        )
        return False

    params = {
        "from": sender,
        "to": to,
        "subject": subject,
    }
    if text:
        params["text"] = text
    if html:
        params["html"] = html
    if attachments:
        params["attachments"] = [
            {
                "filename": att["filename"],
                "content": base64.b64encode(att["content"]).decode(),
                **(
                    {
                        "content_id": att["content_id"],
                        "disposition": att.get("disposition", "inline"),
                    }
                    if att.get("content_id")
                    else {}
                ),
            }
            for att in attachments
        ]

    try:
        resend.api_key = api_key
        response = resend.Emails.send(params)
        if isinstance(response, dict):
            message_id = response.get("id")
        else:
            message_id = getattr(response, "id", None)
        logger.info("Email sent via Resend (id=%s) to %s", message_id, to)
        return True
    except Exception:
        logger.exception("Failed to send email via Resend to %s", to)
        return False
