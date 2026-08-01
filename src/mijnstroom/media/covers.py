import io

from PIL import Image, ImageOps


def fit_cover_art(
    image_bytes: bytes,
    target_size_px: int = 640
) -> bytes:
    input_stream = io.BytesIO(image_bytes)
    with Image.open(input_stream) as img:
        squared_img = ImageOps.pad(
            img, (target_size_px, target_size_px),
            color="black",
            centering=(0.5, 0.5)
        )
        output_stream = io.BytesIO()
        squared_img.convert("RGB").save(
            output_stream, format="JPEG", quality=90
        )
        return output_stream.getvalue()
