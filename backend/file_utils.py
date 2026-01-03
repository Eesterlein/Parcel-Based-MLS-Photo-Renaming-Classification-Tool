"""File saving and naming utilities."""
import shutil
from pathlib import Path
from typing import Optional
import logging
from io import BytesIO
from PIL import Image, ImageFile

# Allow truncated / odd MLS images
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Filename utilities
# ------------------------------------------------------------------

def generate_filename(account_no: str, classification: str, index: int) -> str:
    valid_classifications = {
        "KITCHEN", "LIVING ROOM", "BEDROOM", "OFFICE",
        "DINING ROOM", "LAUNDRY ROOM", "DECK",
        "EXTERIOR", "BATHROOM", "OTHER"
    }

    account_no = str(account_no).upper().strip()
    classification = classification.upper().strip()

    if classification not in valid_classifications:
        classification = "OTHER"

    return f"{account_no} - MLS - {classification} {index}.JPG"


# ------------------------------------------------------------------
# Image loading (Pillow-only, robust)
# ------------------------------------------------------------------

def load_image_safe(image_path: Path) -> Optional[Image.Image]:
    """
    Safely load an image using Pillow only.
    Handles JPG, JPEG, JFIF, WEBP, truncated MLS images.
    """

    # Attempt 1: normal open
    try:
        with Image.open(image_path) as img:
            return img.convert("RGB").copy()
    except Exception as e:
        logger.warning(f"Pillow open failed for {image_path.name}: {e}")

    # Attempt 2: force load
    try:
        img = Image.open(image_path)
        img.load()
        return img.convert("RGB")
    except Exception as e:
        logger.warning(f"Pillow force-load failed for {image_path.name}: {e}")

    # Attempt 3: re-encode through memory
    try:
        with Image.open(image_path) as img:
            buffer = BytesIO()
            img.convert("RGB").save(buffer, format="JPEG", quality=95)
            buffer.seek(0)
            return Image.open(buffer).copy()
    except Exception as e:
        logger.error(f"All Pillow attempts failed for {image_path.name}: {e}")
        return None


# ------------------------------------------------------------------
# Image copy / rename
# ------------------------------------------------------------------

def copy_and_rename_image(
    source_path: Path,
    dest_dir: Path,
    filename: str
) -> Optional[Path]:

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)

        full_path = dest_dir / filename
        counter = 1
        base, ext = full_path.stem, full_path.suffix

        while full_path.exists():
            full_path = dest_dir / f"{base}_{counter}{ext}"
            counter += 1

        shutil.copy2(source_path, full_path)
        logger.info(f"Copied image: {source_path.name} → {full_path.name}")
        return full_path

    except Exception as e:
        logger.error(f"Error copying image {source_path.name}: {e}")
        return None


# ------------------------------------------------------------------
# PDF rename
# ------------------------------------------------------------------

def rename_pdf(pdf_path: Path, account_no: str, output_dir: Path) -> Optional[Path]:

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        account_no = str(account_no).upper().strip()
        full_path = output_dir / f"{account_no}.PDF"

        counter = 1
        while full_path.exists():
            full_path = output_dir / f"{account_no}_{counter}.PDF"
            counter += 1

        shutil.copy2(pdf_path, full_path)
        logger.info(f"Renamed PDF: {pdf_path.name} → {full_path.name}")
        return full_path

    except Exception as e:
        logger.error(f"Error renaming PDF {pdf_path.name}: {e}")
        return None


# ------------------------------------------------------------------
# Output directory validation
# ------------------------------------------------------------------

def ensure_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)

    try:
        path.mkdir(parents=True, exist_ok=True)

        test_file = path / ".write_test"
        test_file.touch()
        test_file.unlink()

        return path

    except Exception as e:
        raise ValueError(f"Output directory is not writable: {output_dir}") from e
