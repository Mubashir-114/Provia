import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse

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
    """
    if isinstance(to, str):
        to = [to]

    if not to:
        return

    try:
        text_body = render_to_string(f"{template_prefix}.txt", context)
        html_body = render_to_string(f"{template_prefix}.html", context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception:
        logger.exception(
            "Failed to send transactional email '%s' to %s",
            subject,
            to,
        )
