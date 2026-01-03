"""Main image processing workflow."""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from backend.folder_parser import extract_parcel_number
from backend.matcher import ParcelMatcher
from backend.image_validator import validate_image_file
from backend.classifier import ImageClassifier
from backend.file_utils import (
    generate_filename,
    copy_and_rename_image,
    rename_pdf,
    load_image_safe,
)

logger = logging.getLogger(__name__)


def process_folder(
    folder_path: str,
    output_dir: str,
    parcel_matcher: ParcelMatcher,
    classifier: ImageClassifier
) -> Dict:
    """
    Process images in selected folder.
    """

    folder = Path(folder_path)
    output = Path(output_dir)

    errors: List[str] = []
    skipped_files: List[str] = []
    results: List[Dict] = []

    # --------------------------------------------------
    # Step 1: Extract parcel number
    # --------------------------------------------------
    logger.info(f"Extracting parcel number from folder name: '{folder.name}'")
    parcel_no = extract_parcel_number(folder.name)

    if not parcel_no:
        errors.append("Could not extract parcel number from folder name")
        logger.warning(errors[-1])

    # --------------------------------------------------
    # Step 2: Match parcel → account
    # --------------------------------------------------
    account_no = "UNKNOWN"

    if parcel_no:
        matched = parcel_matcher.match_parcel_number(parcel_no)
        if matched:
            account_no = matched
            logger.info(f"Matched parcel {parcel_no} to account {account_no}")
        else:
            errors.append(f"No account match found for parcel: {parcel_no}")

    # --------------------------------------------------
    # Step 2.5: Handle PDFs
    # --------------------------------------------------
    logger.info("Processing PDF files...")
    for pdf_file in folder.iterdir():
        if pdf_file.is_file() and pdf_file.suffix.lower() == ".pdf":
            if account_no != "UNKNOWN":
                if not rename_pdf(pdf_file, account_no, output):
                    errors.append(f"Failed to rename PDF: {pdf_file.name}")
            else:
                skipped_files.append(pdf_file.name)

    # --------------------------------------------------
    # Step 3: Scan & load images (Pillow-only)
    # --------------------------------------------------
    logger.info(f"Scanning folder for image files: {folder}")

    valid_extensions = {
        ".jpg", ".jpeg", ".jfif", ".png", ".webp"
    }

    image_files: List[Path] = []

    for file_path in folder.iterdir():
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in valid_extensions:
            continue

        img = load_image_safe(file_path)
        if img is None:
            skipped_files.append(file_path.name)
            errors.append(f"Failed to load image: {file_path.name}")
            continue

        image_files.append(file_path)

    logger.info(f"Found {len(image_files)} image files")

    if not image_files:
        errors.append("No image files found in folder")
        return {
            "account_no": account_no,
            "parcel_no": parcel_no,
            "processed_count": 0,
            "errors": errors,
            "skipped_files": skipped_files,
            "results": results,
        }

    # --------------------------------------------------
    # Step 4: Validate images
    # --------------------------------------------------
    logger.info("Validating image files...")
    valid_images: List[Path] = []

    for image_file in image_files:
        if validate_image_file(image_file):
            valid_images.append(image_file)
        else:
            skipped_files.append(image_file.name)

    logger.info(f"Validated {len(valid_images)} images")

    if not valid_images:
        errors.append("No valid images after validation")
        return {
            "account_no": account_no,
            "parcel_no": parcel_no,
            "processed_count": 0,
            "errors": errors,
            "skipped_files": skipped_files,
            "results": results,
        }

    # --------------------------------------------------
    # Step 5: Classify images
    # --------------------------------------------------
    logger.info("Classifying images...")
    image_paths = [str(img) for img in valid_images]
    classifications = classifier.classify_images(image_paths)

    # --------------------------------------------------
    # Step 6: Group by classification
    # --------------------------------------------------
    grouped = defaultdict(list)
    for image_path, classification in classifications:
        grouped[classification].append(image_path)

    # --------------------------------------------------
    # Step 7: Rename & copy images
    # --------------------------------------------------
    processed_count = 0

    for classification, paths in grouped.items():
        paths.sort()

        for index, image_path in enumerate(paths, start=1):
            filename = generate_filename(account_no, classification, index)
            source_path = Path(image_path)

            copied = copy_and_rename_image(source_path, output, filename)
            if copied:
                processed_count += 1
                results.append({
                    "original_file": source_path.name,
                    "new_filename": filename,
                    "classification": classification,
                    "saved_path": str(copied),
                })
            else:
                errors.append(f"Failed to copy image: {source_path.name}")

    logger.info(f"Processing complete: {processed_count} images processed")

    return {
        "account_no": account_no,
        "parcel_no": parcel_no,
        "processed_count": processed_count,
        "errors": errors,
        "skipped_files": skipped_files,
        "results": results,
    }
