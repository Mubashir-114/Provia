import logging

from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

from config.email_provider import send_email

logger = logging.getLogger(__name__)


def get_site_url():
    """
    Return the configured base URL used to build absolute links inside emails.

    For background tasks (e.g. transaction.on_commit callbacks) no request is
    available, so absolute URLs are built from SITE_URL instead of
    request.build_absolute_uri().
    """
    site_url = getattr(settings, "SITE_URL", "")
    if site_url:
        return site_url.rstrip("/")
    return ""


def build_absolute_url(viewname, *, kwargs=None, args=None):
    """
    Build an absolute URL for a named route without requiring a request object.
    """
    try:
        path = reverse(viewname, kwargs=kwargs, args=args)
    except NoReverseMatch:
        logger.warning("Could not reverse URL for view '%s'", viewname)
        return ""

    site_url = get_site_url()
    if not site_url:
        return path
    return site_url + path


def send_transactional_email(subject, template_prefix, context, to):
    """
    Send a multipart (HTML + plain-text) transactional email.

    Email delivery failures are logged and never propagated to the caller, so
    the primary business operation (booking/payment state transition) is not
    rolled back merely because SMTP failed.
    
    The Provia brand logo is attached as an inline MIME image using Content-ID
    (cid:provia-brand-icon) so it renders reliably in Gmail and other email clients
    without requiring access to the Django development server.
    """
    if isinstance(to, str):
        to = [to]

    if not to:
        return

    try:
        if context is None:
            context = {}
        context.setdefault("site_url", get_site_url())
        text_body = render_to_string(f"{template_prefix}.txt", context)
        html_body = render_to_string(f"{template_prefix}.html", context)

        attachments = None
        logo_path = find("images/branding/provia-banner.jpg")
        if logo_path:
            with open(logo_path, "rb") as f:
                logo_data = f.read()
            attachments = [
                {
                    "filename": "provia-brand-icon.jpg",
                    "content": logo_data,
                    "content_id": "provia-brand-icon",
                    "disposition": "inline",
                }
            ]

        send_email(
            to=to,
            subject=subject,
            text=text_body,
            html=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            attachments=attachments,
        )
    except Exception:
        logger.exception(
            "Failed to send transactional email '%s' to %s",
            subject,
            to,
        )
