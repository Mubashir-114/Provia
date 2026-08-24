#!/usr/bin/env python
"""
Verify that transactional emails use the production-safe absolute HTTPS logo URL
and maintain valid multipart/text-plain MIME structure.
"""

import os
import re
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

print("=" * 70)
print("VERIFYING TRANSACTIONAL EMAIL STRUCTURE & LOGO URL")
print("=" * 70)

try:
    # Use an existing booking email template with production-like site_url
    template_prefix = "bookings/booking_created_customer"
    subject = "Your Provia booking request was received"
    context = {
        "site_url": "https://provia.app",
        "customer_name": "John Doe",
        "provider_name": "Test Provider",
        "service_title": "Cleaning Service",
        "status_display": "Pending",
        "booking_date": "2026-08-25",
        "start_time": "10:00 AM",
        "end_time": "12:00 PM",
        "booking_link": "https://provia.app/bookings/1",
    }

    # Render templates
    print("\n1. Rendering email templates...")
    text_body = render_to_string(f"{template_prefix}.txt", context)
    html_body = render_to_string(f"{template_prefix}.html", context)
    print("   ✓ Text and HTML templates rendered successfully")

    # Construct email
    print("\n2. Constructing email message...")
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["test@example.com"],
    )
    email.attach_alternative(html_body, "text/html")

    # Get the email message
    message = email.message()

    # Validate MIME structure and logo
    print("\n3. Validating MIME structure and logo URL...")

    has_plain_text = False
    has_html = False
    valid_logo_url = False
    logo_src = ""

    for part in message.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":
            has_plain_text = True
            print("   ✓ text/plain part found")
        elif content_type == "text/html":
            has_html = True
            html_content = part.get_payload(decode=True).decode('utf-8')

            # Find logo img tag src
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
            if not match:
                print("   ✗ ERROR: No <img> tag with src found in HTML body")
                sys.exit(1)

            logo_src = match.group(1)
            print(f"   ✓ Found logo src: {logo_src}")

            # 1. contains provia-logo.png
            if "provia-logo.png" not in logo_src:
                print("   ✗ ERROR: Logo src does not contain 'provia-logo.png'")
                sys.exit(1)

            # 2. logo src is absolute HTTPS URL
            if not logo_src.startswith("https://"):
                print(f"   ✗ ERROR: Logo src is not an absolute HTTPS URL (got '{logo_src}')")
                sys.exit(1)

            # 3. NOT referenced using cid:
            if "cid:" in logo_src or "cid:" in html_content:
                print("   ✗ ERROR: Logo or HTML contains forbidden 'cid:' reference")
                sys.exit(1)

            # 4. NOT referenced using a relative /static/ path
            if logo_src.startswith("/static/"):
                print(f"   ✗ ERROR: Logo src is a relative path starting with '/static/'")
                sys.exit(1)

            valid_logo_url = True
            print("   ✓ Logo src is an absolute HTTPS URL with no CID or relative path")

    # Final validation
    print("\n4. Validation Summary:")
    print(f"   {'✓' if has_plain_text else '✗'} Plain-text alternative exists: {has_plain_text}")
    print(f"   {'✓' if has_html else '✗'} HTML alternative exists: {has_html}")
    print(f"   {'✓' if valid_logo_url else '✗'} Absolute HTTPS logo URL validated: {valid_logo_url}")
    print(f"   ✓ Subject: {email.subject}")
    print(f"   ✓ From: {email.from_email}")
    print(f"   ✓ To: {email.to}")

    if all([has_plain_text, has_html, valid_logo_url]):
        print("\n" + "=" * 70)
        print("✓ EMAIL STRUCTURE & LOGO VALIDATION PASSED")
        print("=" * 70)
        print("\nThe email is correctly configured with:")
        print("  • Multipart MIME structure")
        print("  • text/plain alternative for fallback")
        print(f"  • Production-safe absolute HTTPS logo URL ({logo_src})")
    else:
        print("\n✗ EMAIL STRUCTURE VALIDATION FAILED")
        sys.exit(1)

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
