"""
Centralized Category-to-Icon Mapping System for Provia.

Provides clean inline SVG markup for every category in the Provia taxonomy,
with normalization and generic fallback support.
"""

import re
from django.utils.safestring import mark_safe

# Base SVG wrapper class & attributes
DEFAULT_SVG_CLASSES = "h-12 w-12 text-[#b4cdb8] transition-transform duration-200 group-hover:scale-105"

ICON_SVGS = {
    # Cleaning / Housekeeping
    "cleaning": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 21l6-6M14.5 4.5a3 3 0 114 4L9 18l-5 1 1-5 9.5-9.5z"/>
        <path d="M12 2l1.5 3 3 1.5-3 1.5L12 11l-1.5-3L7.5 6.5l3-1.5L12 2z"/>
    </svg>""",

    "deep-cleaning": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 2l2 4 4 2-4 2-2 4-2-4-4-2 4-2 2-4z"/>
        <path d="M5 16l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z"/>
        <path d="M18 14l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z"/>
    </svg>""",

    "housekeeping": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>""",

    "pest-control": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="8" y="6" width="8" height="14" rx="4"/>
        <path d="M6 10h4M14 10h4M4 14h4M16 14h4M6 18h4M14 18h4M12 2v4"/>
    </svg>""",

    "laundry": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M20.38 3.46L16 2a4 4 0 01-8 0L3.62 3.46a2 2 0 00-1.34 2.23l.58 3.47a1 1 0 00.99.84H6v10a2 2 0 002 2h8a2 2 0 002-2V10h2.15a1 1 0 00.99-.84l.58-3.47a2 2 0 00-1.34-2.23z"/>
    </svg>""",

    # Trades & Repairs
    "plumbing": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z"/>
    </svg>""",

    "electrical": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>""",

    "carpentry": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M15 12l-8.5 8.5c-.83.83-2.17.83-3 0 0 0 0 0 0 0-.83-.83-.83-2.17 0-3L12 9"/>
        <path d="M17.64 4.36c.98-.98 2.56-.98 3.54 0 .98.98.98 2.56 0 3.54L14 15l-5-1 1-5 7.64-4.64z"/>
    </svg>""",

    "painting": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M19 11D7 7 0 0 1 5 11V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v6z"/>
        <path d="M12 11v6"/>
        <path d="M8 21h8a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1z"/>
    </svg>""",

    "appliance-repair": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
    </svg>""",

    "home-maintenance": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
        <path d="M9 22V12h6v10"/>
    </svg>""",

    "locksmith": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 2l-2 2m-1.5 1.5L14 9.5M19 5l-2.5 2.5m-.5.5l-2 2"/>
        <circle cx="7.5" cy="16.5" r="4.5"/>
    </svg>""",

    "furniture-assembly": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M20 9V6a2 2 0 00-2-2H6a2 2 0 00-2 2v3M4 11v8a1 1 0 001 1h14a1 1 0 001-1v-8M4 11h16"/>
    </svg>""",

    "moving-packing": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
        <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/>
    </svg>""",

    "gardening-landscaping": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M11 20A7 7 0 019.8 6.1C15.5 5 17 4.4 19 2c1 2 2 4.1 2 7a9 9 0 01-10 11z"/>
        <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
    </svg>""",

    # Beauty & Personal Care
    "hair-salon": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="6" cy="6" r="3"/>
        <circle cx="6" cy="18" r="3"/>
        <line x1="20" y1="4" x2="8.12" y2="15.88"/>
        <line x1="14.47" y1="14.48" x2="20" y2="20"/>
        <line x1="8.12" y1="8.12" x2="12" y2="12"/>
    </svg>""",

    "makeup": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M18 2l-3 3 4 4 3-3-4-4z"/>
        <path d="M14.5 5.5L3 17v4h4L18.5 9.5"/>
    </svg>""",

    "beauty-skincare": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 2l2.4 4.8 5.3.8-3.8 3.7.9 5.3-4.8-2.5-4.8 2.5.9-5.3-3.8-3.7 5.3-.8L12 2z"/>
    </svg>""",

    "nail-care": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M6 3h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5a2 2 0 012-2z"/>
        <path d="M12 7v6M9 10h6"/>
    </svg>""",

    "spa-massage": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M18 11.5c0 3.04-2.46 5.5-5.5 5.5S7 14.54 7 11.5 9.46 6 12.5 6s5.5 2.46 5.5 5.5z"/>
        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
    </svg>""",

    "personal-grooming": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M7 10h10M7 14h10M4 6h16a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V8a2 2 0 012-2z"/>
    </svg>""",

    # Automotive
    "car-repair": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 001 12.4V16c0 .6.4 1 1 1h2"/>
        <circle cx="7" cy="17" r="2"/>
        <circle cx="17" cy="17" r="2"/>
    </svg>""",

    "car-wash-detailing": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 001 12.4V16c0 .6.4 1 1 1h2"/>
        <circle cx="7" cy="17" r="2"/>
        <circle cx="17" cy="17" r="2"/>
        <path d="M12 2l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z"/>
    </svg>""",

    "bike-repair": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="5.5" cy="17.5" r="3.5"/>
        <circle cx="18.5" cy="17.5" r="3.5"/>
        <path d="M15 6a1 1 0 100-2 1 1 0 000 2zm-3 11.5L9.5 10M12 17.5l3.5-7.5H18M5.5 17.5l3.5-7.5h4"/>
    </svg>""",

    "vehicle-inspection": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M9 11l3 3L22 4"/>
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
    </svg>""",

    "tire-wheel-service": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="9"/>
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>
    </svg>""",

    "towing-roadside-assistance": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M14 18V6a2 2 0 00-2-2H4a2 2 0 00-2 2v11a1 1 0 001 1h2"/>
        <path d="M15 18H9"/>
        <path d="M19 18h2a1 1 0 001-1v-3.65a1 1 0 00-.22-.624l-3.48-4.35A1 1 0 0017.52 8H14"/>
        <circle cx="6.5" cy="18.5" r="2.5"/>
        <circle cx="16.5" cy="18.5" r="2.5"/>
    </svg>""",

    # Technology
    "computer-repair": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
    </svg>""",

    "mobile-phone-repair": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
        <line x1="12" y1="18" x2="12.01" y2="18"/>
    </svg>""",

    "it-support": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
        <path d="M8 9l3 3-3 3M13 15h3"/>
    </svg>""",

    "software-development": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="16 18 22 12 16 6"/>
        <polyline points="8 6 2 12 8 18"/>
    </svg>""",

    "web-development": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
    </svg>""",

    "app-development": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
        <path d="M9 9l2 2 4-4"/>
    </svg>""",

    "graphic-design": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 19l7-7 3 3-7 7-3-3z"/>
        <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L11 18l7-5z"/>
        <path d="M2 2l7.58 7.58"/>
        <circle cx="11" cy="11" r="2"/>
    </svg>""",

    "ui-ux-design": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <line x1="3" y1="9" x2="21" y2="9"/>
        <line x1="9" y1="21" x2="9" y2="9"/>
    </svg>""",

    "data-analytics": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <line x1="18" y1="20" x2="18" y2="10"/>
        <line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>""",

    "digital-marketing": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M22 12A10 10 0 0012 2v10z"/>
        <path d="M12 21A9 9 0 103 12h9z"/>
    </svg>""",

    "photography-video-editing": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
        <circle cx="12" cy="13" r="4"/>
    </svg>""",

    # Education
    "academic-tutoring": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
    </svg>""",

    "language-learning": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M5 8l6 6M4 14l6-6 2 3M2 5h12M7 2v3"/>
        <path d="M22 22l-5-10-5 10M14 18h6"/>
    </svg>""",

    "music-lessons": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M9 18V5l12-2v13"/>
        <circle cx="6" cy="18" r="3"/>
        <circle cx="18" cy="16" r="3"/>
    </svg>""",

    "coding-programming": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="4 17 10 11 4 5"/>
        <line x1="12" y1="19" x2="20" y2="19"/>
    </svg>""",

    "exam-preparation": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
        <path d="M6 12v5c3 3 9 3 12 0v-5"/>
    </svg>""",

    "professional-training": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
    </svg>""",

    # Professional Services
    "accounting-bookkeeping": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="4" y="2" width="16" height="20" rx="2"/>
        <line x1="8" y1="6" x2="16" y2="6"/>
        <line x1="16" y1="14" x2="16" y2="18"/>
        <path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01"/>
    </svg>""",

    "legal-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 3v18M3 7l4 8h-8zM21 7l4 8h-8zM3 7h18"/>
    </svg>""",

    "business-consulting": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
        <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/>
    </svg>""",

    "career-coaching": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
        <circle cx="8.5" cy="7" r="4"/>
        <polyline points="17 11 19 13 23 9"/>
    </svg>""",

    "resume-interview-help": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>""",

    "tax-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <line x1="12" y1="1" x2="12" y2="23"/>
        <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
    </svg>""",

    "translation": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M5 8l6 6M4 14l6-6 2 3M2 5h12M7 2v3"/>
        <path d="M22 22l-5-10-5 10M14 18h6"/>
    </svg>""",

    # Events
    "event-planning": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>""",

    "catering": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9z"/>
        <path d="M13.73 21a2 2 0 01-3.46 0"/>
    </svg>""",

    "wedding-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
    </svg>""",

    "photography": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
        <circle cx="12" cy="13" r="4"/>
    </svg>""",

    "videography": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polygon points="23 7 16 12 23 17 23 7"/>
        <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
    </svg>""",

    "dj-music": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M9 18V5l12-2v13"/>
        <circle cx="6" cy="18" r="3"/>
        <circle cx="18" cy="16" r="3"/>
    </svg>""",

    "decoration": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 2l2.4 4.8 5.3.8-3.8 3.7.9 5.3-4.8-2.5-4.8 2.5.9-5.3-3.8-3.7 5.3-.8L12 2z"/>
    </svg>""",

    # Health & Wellness
    "fitness-training": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M6.5 6.5h11M6.5 17.5h11M3 9.5v5M21 9.5v5M4.5 8v8M19.5 8v8M8 6.5v11M16 6.5v11"/>
    </svg>""",

    "yoga": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="4" r="2"/>
        <path d="M12 6v6m0 0l-4 4m4-4l4 4M6 9l6 3 6-3"/>
    </svg>""",

    "nutrition-coaching": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 18a8 8 0 118-8 8 8 0 01-8 8z"/>
        <path d="M12 6a6 6 0 00-6 6h6z"/>
    </svg>""",

    "wellness-coaching": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
    </svg>""",

    # Delivery & Logistics
    "local-delivery": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>
        <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
        <line x1="12" y1="22.08" x2="12" y2="12"/>
    </svg>""",

    "courier-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="1" y="3" width="15" height="13" rx="2" ry="2"/>
        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
        <circle cx="5.5" cy="18.5" r="2.5"/>
        <circle cx="18.5" cy="18.5" r="2.5"/>
    </svg>""",

    "moving-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="1" y="3" width="15" height="13" rx="2" ry="2"/>
        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
        <circle cx="5.5" cy="18.5" r="2.5"/>
        <circle cx="18.5" cy="18.5" r="2.5"/>
    </svg>""",

    "driver-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 001 12.4V16c0 .6.4 1 1 1h2"/>
        <circle cx="7" cy="17" r="2"/>
        <circle cx="17" cy="17" r="2"/>
    </svg>""",

    # Outdoor & Lifestyle
    "pet-care": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 14c-3 0-5 2-5 4s2 3 5 3 5-1 5-3-2-4-5-4z"/>
        <circle cx="7" cy="8" r="2"/>
        <circle cx="17" cy="8" r="2"/>
        <circle cx="12" cy="6" r="2"/>
    </svg>""",

    "dog-walking": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 14c-3 0-5 2-5 4s2 3 5 3 5-1 5-3-2-4-5-4z"/>
        <circle cx="7" cy="8" r="2"/>
        <circle cx="17" cy="8" r="2"/>
        <circle cx="12" cy="6" r="2"/>
    </svg>""",

    "pet-grooming": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="6" cy="6" r="3"/>
        <circle cx="6" cy="18" r="3"/>
        <line x1="20" y1="4" x2="8.12" y2="15.88"/>
        <line x1="14.47" y1="14.48" x2="20" y2="20"/>
    </svg>""",

    "gardening": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M11 20A7 7 0 019.8 6.1C15.5 5 17 4.4 19 2c1 2 2 4.1 2 7a9 9 0 01-10 11z"/>
        <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
    </svg>""",

    "travel-assistance": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/>
        <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
    </svg>""",

    # Generic Fallback / Shapes
    "other-services": """<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
    </svg>""",
}


def normalize_category_key(key):
    """
    Normalizes a category name or slug to a matching lookup key.
    E.g., "Home Cleaning" -> "cleaning", "Deep Cleaning" -> "deep-cleaning".
    """
    if not key:
        return "other-services"

    if hasattr(key, "slug"):
        slug = key.slug
    elif hasattr(key, "name"):
        slug = key.name
    else:
        slug = str(key)

    # Convert to lowercase and strip
    slug = slug.lower().strip()

    # Direct match in ICON_SVGS keys
    if slug in ICON_SVGS:
        return slug

    # Replace non-alphanumeric with hyphen
    hyphenated = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    if hyphenated in ICON_SVGS:
        return hyphenated

    # Partial / keyword matching fallbacks
    if "carpenter" in hyphenated or "carpentry" in hyphenated or "wood" in hyphenated:
        return "carpentry"
    if "clean" in hyphenated:
        return "cleaning"
    if "plumb" in hyphenated:
        return "plumbing"
    if "electr" in hyphenated:
        return "electrical"
    if "car-repair" in hyphenated or "mechanic" in hyphenated:
        return "car-repair"
    if "car" in hyphenated and "wash" in hyphenated:
        return "car-wash-detailing"
    if "car" in hyphenated or "auto" in hyphenated:
        return "car-repair"
    if "pest" in hyphenated:
        return "pest-control"
    if "laundry" in hyphenated or "wash" in hyphenated:
        return "laundry"
    if "hair" in hyphenated or "salon" in hyphenated:
        return "hair-salon"
    if "makeup" in hyphenated:
        return "makeup"
    if "spa" in hyphenated or "massage" in hyphenated:
        return "spa-massage"
    if "computer" in hyphenated or "pc" in hyphenated or "laptop" in hyphenated:
        return "computer-repair"
    if "phone" in hyphenated or "mobile" in hyphenated:
        return "mobile-phone-repair"
    if "web" in hyphenated:
        return "web-development"
    if "app" in hyphenated:
        return "app-development"
    if "code" in hyphenated or "program" in hyphenated or "software" in hyphenated:
        return "coding-programming"
    if "photo" in hyphenated:
        return "photography"
    if "video" in hyphenated:
        return "videography"
    if "tutor" in hyphenated or "teacher" in hyphenated:
        return "academic-tutoring"
    if "legal" in hyphenated or "law" in hyphenated:
        return "legal-services"
    if "tax" in hyphenated or "account" in hyphenated:
        return "accounting-bookkeeping"
    if "cater" in hyphenated or "food" in hyphenated:
        return "catering"
    if "event" in hyphenated:
        return "event-planning"
    if "fit" in hyphenated or "gym" in hyphenated:
        return "fitness-training"
    if "yoga" in hyphenated:
        return "yoga"
    if "pet" in hyphenated or "dog" in hyphenated:
        return "pet-care"
    if "deliver" in hyphenated or "courier" in hyphenated or "ship" in hyphenated:
        return "local-delivery"
    if "move" in hyphenated or "pack" in hyphenated:
        return "moving-packing"
    if "garden" in hyphenated or "lawn" in hyphenated:
        return "gardening-landscaping"
    if "lock" in hyphenated:
        return "locksmith"

    return "other-services"


def get_category_icon_svg(category, extra_classes=None):
    """
    Returns mark_safe HTML string containing the SVG icon for a given category.
    """
    key = normalize_category_key(category)
    svg_template = ICON_SVGS.get(key, ICON_SVGS["other-services"])
    classes = extra_classes if extra_classes else DEFAULT_SVG_CLASSES
    return mark_safe(svg_template.format(classes=classes))
