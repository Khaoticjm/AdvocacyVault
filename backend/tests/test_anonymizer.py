import io
import struct
import pytest
from PIL import Image
from app.modules.anonymizer.utils import scrub_exif


def _make_jpeg_with_gps() -> bytes:
    """Create a minimal JPEG with GPS EXIF data."""
    import piexif
    img = Image.new("RGB", (100, 100), color=(128, 64, 32))
    buf = io.BytesIO()
    exif_dict = {
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((33, 1), (45, 1), (0, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((84, 1), (23, 1), (0, 1)),
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2024:03:15 14:23:00",
        },
        "0th": {},
        "1st": {},
        "thumbnail": None,
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(buf, format="JPEG", exif=exif_bytes)
    return buf.getvalue()


def _make_png() -> bytes:
    img = Image.new("RGB", (100, 100), color=(64, 128, 192))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_jpeg_gps_removed():
    import piexif
    jpeg_with_gps = _make_jpeg_with_gps()
    scrubbed = scrub_exif(jpeg_with_gps, "image/jpeg")
    exif = piexif.load(scrubbed)
    assert exif.get("GPS", {}) == {}


def test_jpeg_datetime_removed():
    import piexif
    jpeg = _make_jpeg_with_gps()
    scrubbed = scrub_exif(jpeg, "image/jpeg")
    exif = piexif.load(scrubbed)
    assert piexif.ExifIFD.DateTimeOriginal not in exif.get("Exif", {})


def test_jpeg_still_valid_image_after_scrub():
    jpeg = _make_jpeg_with_gps()
    scrubbed = scrub_exif(jpeg, "image/jpeg")
    img = Image.open(io.BytesIO(scrubbed))
    assert img.format == "JPEG"


def test_png_scrub_produces_valid_image():
    png = _make_png()
    scrubbed = scrub_exif(png, "image/png")
    img = Image.open(io.BytesIO(scrubbed))
    assert img.format == "PNG"


def test_unsupported_type_returned_unchanged():
    data = b"fake pdf content"
    result = scrub_exif(data, "application/pdf")
    assert result == data


def test_jpeg_content_type_alias():
    jpeg = _make_jpeg_with_gps()
    scrubbed = scrub_exif(jpeg, "image/jpg")
    img = Image.open(io.BytesIO(scrubbed))
    assert img.format == "JPEG"
