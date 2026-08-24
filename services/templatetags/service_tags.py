from django import template
from services.category_icons import get_category_icon_svg

register = template.Library()


@register.simple_tag
def category_icon_svg(category, extra_classes=None):
    """
    Renders the centralized category fallback SVG icon for a given category instance or category name.
    """
    return get_category_icon_svg(category, extra_classes=extra_classes)


@register.filter
def has_service_image(service):
    """
    Returns True if service object has a non-null, non-empty image.
    """
    if not service:
        return False
    image = getattr(service, "image", None)
    return bool(image)
