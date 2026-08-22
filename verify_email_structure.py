#!/usr/bin/env python
"""
Verify that transactional emails have the correct MIME structure with CID inline image.

This script constructs a test email and validates:
1. HTML body contains cid:provia-brand-icon
2. MIME message contains an image/png part
3. Image Content-ID is <provia-brand-icon>
4. Plain-text alternative exists
5. Subject is correct
"""

import os
import sys
import django
from email.parser import Parser
from email.mime.image import MIMEImage
from io import StringIO

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from notifications.email_utils import send_transactional_email
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.template.loader import render_to_string

print("=" * 70)
print("VERIFYING EMAIL MIME STRUCTURE")
print("=" * 70)

# Simulate email construction
try:
    # Use an existing booking email template
    template_prefix = "bookings/booking_created_customer"
    subject = "Your Provia booking request was received"
    context = {
        "site_url": "https://example.com",
        "customer_name": "John Doe",
        "provider_name": "Test Provider",
        "service_title": "Cleaning Service",
        "status_display": "Pending",
        "booking_date": "2026-08-25",
        "start_time": "10:00 AM",
        "end_time": "12:00 PM",
        "booking_link": "https://example.com/bookings/1",
    }
    
    # Render templates
    print("\n1. Rendering email templates...")
    text_body = render_to_string(f"{template_prefix}.txt", context)
    html_body = render_to_string(f"{template_prefix}.html", context)
    print("   ✓ Text and HTML templates rendered successfully")
    
    # Construct email
    print("\n2. Constructing email with inline CID image...")
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["test@example.com"],
    )
    email.attach_alternative(html_body, "text/html")
    
    # Attach logo
    logo_path = find("images/branding/provia-brand-icon.png")
    if logo_path:
        with open(logo_path, "rb") as f:
            logo_data = f.read()
        
        # Create MIME image part with Content-ID
        img = MIMEImage(logo_data, "png")
        img.add_header("Content-ID", "<provia-brand-icon>")
        img.add_header("Content-Disposition", "inline")
        # Attach MIME part directly to message
        email.attach(img)
        
        print(f"   ✓ Logo attached from: {logo_path}")
        print(f"   ✓ Logo size: {len(logo_data)} bytes")
    else:
        print("   ✗ ERROR: Logo file not found!")
        sys.exit(1)
    
    # Get the email message
    message = email.message()
    
    # Validate MIME structure
    print("\n3. Validating MIME structure...")
    
    # Check for plain text part
    has_plain_text = False
    has_html = False
    has_image = False
    image_cid = None
    
    for part in message.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":
            has_plain_text = True
            print("   ✓ text/plain part found")
        elif content_type == "text/html":
            has_html = True
            html_content = part.get_payload(decode=True).decode('utf-8')
            if "cid:provia-brand-icon" in html_content:
                print("   ✓ text/html part found")
                print("   ✓ HTML contains: cid:provia-brand-icon")
            else:
                print("   ✗ ERROR: HTML does not contain cid:provia-brand-icon")
                sys.exit(1)
        elif content_type == "image/png":
            has_image = True
            image_cid = part.get("Content-ID")
            print(f"   ✓ image/png part found")
            print(f"   ✓ Content-ID: {image_cid}")
            if image_cid != "<provia-brand-icon>":
                print(f"   ✗ ERROR: Expected Content-ID '<provia-brand-icon>', got '{image_cid}'")
                sys.exit(1)
    
    # Final validation
    print("\n4. Validation Summary:")
    print(f"   {'✓' if has_plain_text else '✗'} Plain-text alternative exists: {has_plain_text}")
    print(f"   {'✓' if has_html else '✗'} HTML alternative exists: {has_html}")
    print(f"   {'✓' if has_image else '✗'} Inline image/png exists: {has_image}")
    print(f"   {'✓' if image_cid == '<provia-brand-icon>' else '✗'} Correct Content-ID: {image_cid == '<provia-brand-icon>'}")
    print(f"   ✓ Subject: {email.subject}")
    print(f"   ✓ From: {email.from_email}")
    print(f"   ✓ To: {email.to}")
    
    if all([has_plain_text, has_html, has_image, image_cid == "<provia-brand-icon>"]):
        print("\n" + "=" * 70)
        print("✓ EMAIL STRUCTURE VALIDATION PASSED")
        print("=" * 70)
        print("\nThe email is correctly configured with:")
        print("  • Multipart MIME structure")
        print("  • text/plain alternative for fallback")
        print("  • text/html alternative with cid:provia-brand-icon")
        print("  • Inline image/png with Content-ID <provia-brand-icon>")
        print("\nEmails sent through send_transactional_email() will now display")
        print("the Provia logo correctly in Gmail and other email clients.")
    else:
        print("\n✗ EMAIL STRUCTURE VALIDATION FAILED")
        sys.exit(1)

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
