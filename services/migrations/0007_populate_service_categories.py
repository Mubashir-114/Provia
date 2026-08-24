from django.db import migrations
from django.utils.text import slugify

CATEGORIES = [
    # Home & Cleaning
    ("Cleaning", "Professional home and office cleaning services."),
    ("Deep Cleaning", "Thorough deep cleaning for residences and spaces."),
    ("Housekeeping", "Regular housekeeping and maid services."),
    ("Pest Control", "Inspection, prevention, and removal of pests."),
    ("Laundry", "Washing, dry cleaning, and ironing services."),
    ("Plumbing", "Pipe repair, leak fixing, and plumbing installation."),
    ("Electrical", "Electrical wiring, fixtures, and system repairs."),
    ("Carpentry", "Woodwork, custom cabinetry, and furniture repair."),
    ("Painting", "Interior and exterior painting services."),
    ("Appliance Repair", "Repair and maintenance for major home appliances."),
    ("Home Maintenance", "General handyman and home repair services."),
    ("Locksmith", "Key cutting, lock installation, and emergency lockout."),
    ("Furniture Assembly", "Assembly and setup of flat-pack furniture."),
    ("Moving & Packing", "Relocation, packing, and heavy lifting."),
    ("Gardening & Landscaping", "Lawn care, garden maintenance, and landscaping."),

    # Beauty & Personal Care
    ("Hair & Salon", "Haircuts, styling, coloring, and hair treatments."),
    ("Makeup", "Professional makeup for events, weddings, and photoshoots."),
    ("Beauty & Skincare", "Facials, skincare routines, and beauty treatments."),
    ("Nail Care", "Manicures, pedicures, and nail art."),
    ("Spa & Massage", "Therapeutic massage and wellness spa treatments."),
    ("Personal Grooming", "Barbering, shaving, and personal grooming."),

    # Automotive
    ("Car Repair", "Automotive mechanical diagnostics and engine repair."),
    ("Car Wash & Detailing", "Exterior washing, interior detailing, and polishing."),
    ("Bike Repair", "Motorcycle and bicycle servicing and repairs."),
    ("Vehicle Inspection", "Pre-purchase and safety vehicle inspections."),
    ("Tire & Wheel Service", "Tire replacement, balancing, and alignment."),
    ("Towing & Roadside Assistance", "24/7 vehicle recovery and roadside help."),

    # Technology
    ("Computer Repair", "Hardware repair, virus removal, and PC setup."),
    ("Mobile Phone Repair", "Screen replacement, battery repair, and mobile fixes."),
    ("IT Support", "Network setup, troubleshooting, and tech support."),
    ("Software Development", "Custom software engineering and backend systems."),
    ("Web Development", "Website creation, frontend design, and web apps."),
    ("App Development", "Mobile app design and development for iOS and Android."),
    ("Graphic Design", "Branding, logos, marketing graphics, and visual design."),
    ("UI/UX Design", "User interface and experience design for digital products."),
    ("Data & Analytics", "Data processing, reporting, and business intelligence."),
    ("Digital Marketing", "SEO, social media management, and online advertising."),
    ("Photography & Video Editing", "Media editing, post-production, and touch-ups."),

    # Education
    ("Academic Tutoring", "K-12 and university academic subject tutoring."),
    ("Language Learning", "Foreign language instruction and conversation practice."),
    ("Music Lessons", "Instrument and vocal music lessons."),
    ("Coding & Programming", "Software engineering and coding instruction."),
    ("Exam Preparation", "Standardized test prep and study coaching."),
    ("Professional Training", "Corporate skills, certification, and vocational training."),

    # Professional Services
    ("Accounting & Bookkeeping", "Financial recordkeeping, payroll, and bookkeeping."),
    ("Legal Services", "Legal advice, document drafting, and consultation."),
    ("Business Consulting", "Strategy, operations, and growth advisory."),
    ("Career Coaching", "Resume building, career guidance, and interview prep."),
    ("Resume & Interview Help", "Professional resume writing and mock interviews."),
    ("Tax Services", "Tax preparation, filing, and tax planning."),
    ("Translation", "Language translation and localization services."),

    # Events
    ("Event Planning", "Full-service event coordination and planning."),
    ("Catering", "Food service and catering for events and parties."),
    ("Wedding Services", "Wedding planning, coordination, and services."),
    ("Photography", "Event, portrait, and commercial photography."),
    ("Videography", "Video recording and production for events."),
    ("DJ & Music", "Live music, DJ performance, and sound setup."),
    ("Decoration", "Venue decoration and floral arrangements."),

    # Health & Wellness
    ("Fitness Training", "Personal training, workouts, and fitness coaching."),
    ("Yoga", "Yoga classes, meditation, and mindfulness coaching."),
    ("Nutrition Coaching", "Meal planning and dietary guidance."),
    ("Wellness Coaching", "Holistic health and wellness lifestyle coaching."),

    # Delivery & Logistics
    ("Local Delivery", "Same-day local package dispatch and pickup."),
    ("Courier Services", "Document and parcel express courier service."),
    ("Moving Services", "Local freight and item transport services."),
    ("Driver Services", "Chauffeur and personal driver services."),

    # Outdoor & Lifestyle
    ("Pet Care", "Pet sitting, boarding, and companion care."),
    ("Dog Walking", "Daily dog walking and exercise."),
    ("Pet Grooming", "Bathing, haircutting, and styling for pets."),
    ("Gardening", "Plant care, pruning, and garden upkeep."),
    ("Travel Assistance", "Travel planning, itinerary help, and booking."),

    # Other
    ("Other Services", "Custom and specialized service offerings."),
]


def populate_categories(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    for name, description in CATEGORIES:
        slug = slugify(name)
        ServiceCategory.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "is_active": True,
            },
        )


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0006_service_image"),
    ]

    operations = [
        migrations.RunPython(populate_categories, reverse_populate),
    ]
