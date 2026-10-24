import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def scrub_exif(file_bytes: bytes, content_type: str) -> bytes:
    """
    Remove identifying EXIF metadata from images before persistence.
    - JPEG: zero out GPS IFD and DateTimeOriginal via piexif
    - PNG: re-encode through Pillow (strips all ancillary chunks)
    - Other: return unchanged with a warning
    """
    if content_type in ("image/jpeg", "image/jpg"):
        return _scrub_jpeg(file_bytes)
    elif content_type == "image/png":
        return _scrub_png(file_bytes)
    else:
        logger.warning("EXIF scrubbing not supported for content_type=%s — storing as-is", content_type)
        return file_bytes


def _scrub_jpeg(data: bytes) -> bytes:
    try:
        import piexif
        exif = piexif.load(data)
        # Zero out GPS and datetime
        exif["GPS"] = {}
        if piexif.ImageIFD.DateTime in exif.get("0th", {}):
            del exif["0th"][piexif.ImageIFD.DateTime]
        if piexif.ExifIFD.DateTimeOriginal in exif.get("Exif", {}):
            del exif["Exif"][piexif.ExifIFD.DateTimeOriginal]
        if piexif.ExifIFD.DateTimeDigitized in exif.get("Exif", {}):
            del exif["Exif"][piexif.ExifIFD.DateTimeDigitized]
        exif_bytes = piexif.dump(exif)
        return piexif.insert(exif_bytes, data)
    except Exception as exc:
        logger.error("JPEG EXIF scrub failed: %s — re-encoding through Pillow", exc)
        return _pillow_reencode(data, "JPEG")


def _scrub_png(data: bytes) -> bytes:
    return _pillow_reencode(data, "PNG")


def _pillow_reencode(data: bytes, fmt: str) -> bytes:
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()
