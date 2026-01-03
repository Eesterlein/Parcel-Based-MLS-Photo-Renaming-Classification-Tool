"""Image validation utilities."""
import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)


def validate_image_file(file_path: Path) -> bool:
    """
    Validate that a file is a readable image.

    This validator is intentionally permissive.
    If Pillow can open the image, it is considered valid.
    """

    if not file_path.exists():
        logger.debug(f"File does not exist: {file_path}")
        return False

    try:
        with Image.open(file_path) as img:
            img.load()  # force decode
        return True

    except Exception as e:
        logger.debug(f"Invalid image file {file_path.name}: {e}")
        return False
