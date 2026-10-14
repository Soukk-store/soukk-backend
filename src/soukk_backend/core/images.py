from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from soukk_backend.domains.users.userExceptions import InvalidImage

ACCEPTED_FORMATS = ("JPEG", "PNG", "WEBP")
OUTPUT_CONTENT_TYPE = "image/webp"
# A small file can still declare huge dimensions and take gigabytes to decode
# (a "decompression bomb"). Opening only reads the header, so check before decoding.
MAX_PIXELS = 40_000_000


def process_avatar(data: bytes, size_px: int) -> bytes:
    """Turn an uploaded image into a square WebP of size_px pixels.

    Decoding and re-encoding also drops anything that isn't pixels: EXIF (GPS,
    camera), comments and any payload hidden after the image data.
    """
    try:
        with Image.open(BytesIO(data), formats=ACCEPTED_FORMATS) as image:
            if image.width * image.height > MAX_PIXELS:
                raise InvalidImage()
            image.load()
            # Phones store rotation as an EXIF tag, which is about to be dropped.
            image = ImageOps.exif_transpose(image)
            has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            image = ImageOps.fit(image, (size_px, size_px), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
        raise InvalidImage() from error

    out = BytesIO()
    image.save(out, "WEBP", quality=85)
    return out.getvalue()
