"""Email transport abstraction for Provia.

Sends mail through the Brevo HTTPS API when ``BREVO_API_KEY`` is configured,
otherwise it falls back to Django's configured ``EMAIL_BACKEND`` (e.g. local
Gmail SMTP or the ``locmem`` backend used in tests). This keeps the existing
localhost/Gmail behaviour intact while allowing Render Free (which blocks
outbound SMTP on ports 25/465/587) to deliver mail over HTTPS.

Neither the API key nor any credential is ever logged.
"""
import base64
import logging

from django.conf import settings

import brevo
from brevo.core.api_error import ApiError
from brevo.transactional_emails import (
    SendTransacEmailRequestAttachmentItem,
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

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

    api_key = getattr(settings, "BREVO_API_KEY", "") or ""
    sender = (
        from_email
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or "noreply@localhost"
    )

    if api_key:
        return _send_via_brevo(api_key, sender, to, subject, text, html, attachments)
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


def _send_via_brevo(api_key, sender, to, subject, text, html, attachments):
    try:
        client = brevo.Brevo(api_key=api_key)

        sender_name, sender_email = _parse_sender(sender)
        to_items = [_to_item(addr) for addr in to]

        brevo_attachments = None
        if attachments:
            brevo_attachments = [_attachment_item(att) for att in attachments]

        response = client.transactional_emails.send_transac_email(
            sender=SendTransacEmailRequestSender(
                email=sender_email,
                name=sender_name,
            ),
            to=to_items,
            subject=subject,
            text_content=text,
            html_content=html,
            attachment=brevo_attachments,
        )
        message_id = getattr(response, "message_id", None)
        logger.info("Email sent via Brevo (id=%s) to %s", message_id, to)
        return True
    except ApiError:
        logger.exception("Failed to send email via Brevo to %s", to)
        return False
    except Exception:
        logger.exception("Failed to send email via Brevo to %s", to)
        return False


def _parse_sender(sender):
    if "<" in sender and ">" in sender:
        name = sender.split("<")[0].strip()
        email = sender.split("<")[1].split(">")[0].strip()
        return name, email
    return "", sender


def _to_item(email_addr):
    if "<" in email_addr and ">" in email_addr:
        name = email_addr.split("<")[0].strip()
        email = email_addr.split("<")[1].split(">")[0].strip()
        return SendTransacEmailRequestToItem(email=email, name=name)
    return SendTransacEmailRequestToItem(email=email_addr)


def _attachment_item(att):
    filename = att.get("filename", "")
    base64_content = base64.b64encode(att["content"]).decode("utf-8")
    return SendTransacEmailRequestAttachmentItem(
        name=filename,
        content=base64_content,
    )
