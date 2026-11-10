"""Re-encode staff uploads: strips EXIF/GPS metadata, fixes orientation and bounds the size."""
import io
import uuid
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_EDGE = 1600
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def validate_upload(upload):
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError('Images must be 5 MB or smaller.')
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.verify()
            if image.format not in ALLOWED_FORMATS:
                raise ValidationError('Upload a JPEG, PNG or WebP image.')
    except ValidationError:
        raise
    except Exception:
        raise ValidationError('This file is not a readable image.')
    finally:
        upload.seek(0)


def clean_image(upload, prefix):
    with Image.open(upload) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((MAX_EDGE, MAX_EDGE))
        has_alpha = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
        image = image.convert('RGBA' if has_alpha else 'RGB')
        buffer = io.BytesIO()
        if has_alpha:
            image.save(buffer, 'PNG', optimize=True)
            extension = 'png'
        else:
            image.save(buffer, 'JPEG', quality=85, optimize=True)
            extension = 'jpg'
    return ContentFile(buffer.getvalue(), name=f'{prefix}-{uuid.uuid4().hex[:12]}.{extension}')
