from django.core.exceptions import ValidationError

from PIL import Image

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


def validate_image_file(file_obj):
    if file_obj.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            "Image file too large ( > 5MB )."
        )

    try:
        file_obj.seek(0)
        image = Image.open(file_obj)
        file_obj.seek(0)
    except Exception:
        raise ValidationError(
            "Invalid image file."
        )

    if image.format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            "Unsupported file type. Use JPG, PNG, or WEBP."
        )
