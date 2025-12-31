"""File saving and naming utilities."""
import shutil
from pathlib import Path
from typing import Optional
import logging
from PIL import Image

logger = logging.getLogger(__name__)


def generate_filename(account_no: str, classification: str, index: int) -> str:
    """
    Generate filename according to convention.
    
    Format: ACCOUNTNO – MLS – ROOMTYPE X.JPG
    - ALL CAPS
    - Spaces before and after dashes
    - Sequential numbering per room type
    
    Args:
        account_no: Account number (will be uppercased)
        classification: Room classification (already ALL CAPS)
        index: Sequential number for this room type (1, 2, 3...)
        
    Returns:
        Filename string in format: ACCOUNTNO – MLS – ROOMTYPE X.JPG
    """
    # Ensure classification is valid and ALL CAPS (matches three-layer classifier labels)
    valid_classifications = {
        'KITCHEN', 'LIVING ROOM', 'BEDROOM', 'OFFICE',
        'DINING ROOM', 'LAUNDRY ROOM', 'DECK', 'EXTERIOR', 'BATHROOM', 'OTHER'
    }
    
    # Normalize classification to ALL CAPS
    classification = classification.upper().strip()
    
    if classification not in valid_classifications:
        classification = 'OTHER'
    
    # Ensure account number is ALL CAPS
    account_no = str(account_no).upper().strip()
    
    # Format: ACCOUNTNO - MLS - ROOMTYPE X.JPG
    # Using regular dash with spaces as specified: " - "
    filename = f"{account_no} - MLS - {classification} {index}.JPG"
    return filename


def copy_and_rename_image(
    source_path: Path, 
    dest_dir: Path, 
    filename: str
) -> Optional[Path]:
    """
    Copy image file and rename it according to naming convention.
    
    Args:
        source_path: Path to source image file
        dest_dir: Directory to copy image to
        filename: New filename to use
        
    Returns:
        Full path to copied file, or None if failed
    """
    try:
        # Ensure output directory exists
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle filename collisions
        full_path = dest_dir / filename
        counter = 1
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        ext = filename.rsplit('.', 1)[1] if '.' in filename else 'JPG'
        
        while full_path.exists():
            # Add counter before extension
            new_filename = f"{base_name}_{counter}.{ext}"
            full_path = dest_dir / new_filename
            counter += 1
        
        # Copy file
        shutil.copy2(source_path, full_path)
        
        logger.info(f"Copied and renamed image: {source_path.name} -> {full_path.name}")
        return full_path
        
    except Exception as e:
        logger.error(f"Error copying image {source_path}: {e}")
        return None


def rename_pdf(pdf_path: Path, account_no: str, output_dir: Path) -> Optional[Path]:
    """
    Rename PDF file to just the account number.
    
    Args:
        pdf_path: Path to PDF file
        account_no: Account number to use in filename
        output_dir: Directory to copy renamed PDF to
        
    Returns:
        Full path to renamed PDF, or None if failed
    """
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: ACCOUNTNO.PDF
        account_no = str(account_no).upper().strip()
        filename = f"{account_no}.PDF"
        
        # Handle filename collisions
        full_path = output_dir / filename
        counter = 1
        base_name = account_no
        
        while full_path.exists():
            # Add counter before extension
            new_filename = f"{base_name}_{counter}.PDF"
            full_path = output_dir / new_filename
            counter += 1
        
        # Copy PDF file
        shutil.copy2(pdf_path, full_path)
        
        logger.info(f"Renamed PDF: {pdf_path.name} -> {full_path.name}")
        return full_path
        
    except Exception as e:
        logger.error(f"Error renaming PDF {pdf_path}: {e}")
        return None


def convert_to_jpeg(source_path: Path, output_dir: Path) -> Optional[Path]:
    """
    Convert image file to JPEG format.
    
    Args:
        source_path: Path to source image file
        output_dir: Directory to save converted JPEG
        
    Returns:
        Full path to converted JPEG file, or None if failed
    """
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load image
        img = Image.open(source_path)
        
        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode != 'RGB':
            # Create white background for transparency
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            else:
                rgb_img.paste(img)
            img = rgb_img
        
        # Generate output filename (same name but .jpg extension)
        base_name = source_path.stem
        output_filename = f"{base_name}.JPG"
        output_path = output_dir / output_filename
        
        # Handle filename collisions
        counter = 1
        while output_path.exists():
            output_filename = f"{base_name}_{counter}.JPG"
            output_path = output_dir / output_filename
            counter += 1
        
        # Save as JPEG with high quality
        img.save(output_path, 'JPEG', quality=95)
        
        logger.info(f"Converted to JPEG: {source_path.name} -> {output_path.name}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error converting image {source_path} to JPEG: {e}")
        return None


def ensure_output_dir(output_dir: str) -> Path:
    """
    Ensure output directory exists and is writable.
    
    Args:
        output_dir: Output directory path
        
    Returns:
        Path object
        
    Raises:
        ValueError: If directory cannot be created or is not writable
    """
    path = Path(output_dir)
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise ValueError(f"Output directory is not writable: {output_dir}") from e
        
        return path
        
    except Exception as e:
        raise ValueError(f"Cannot create output directory: {output_dir}") from e


