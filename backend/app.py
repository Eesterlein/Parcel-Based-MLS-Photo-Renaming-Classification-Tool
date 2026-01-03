"""Main application entry point for MLS Photo Processor."""
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from backend.matcher import ParcelMatcher
from backend.classifier import ImageClassifier
from backend.processor import process_folder
from backend.gui import MLSPhotoProcessorGUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mls_photo_processor.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    logger.info("Starting MLS Photo Processor...")

    # ---- Session tracking ----
    SESSION_START_TIME = time.time()
    SESSION_ID = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    logger.info(f"SESSION_START id={SESSION_ID}")

    try:
        # Initialize components
        logger.info("Loading parcel matcher...")
        parcel_matcher = ParcelMatcher()
        logger.info("Parcel matcher loaded successfully")

        logger.info("Loading image classifier...")
        classifier = ImageClassifier()
        logger.info("Image classifier loaded successfully")

        # Create GUI
        logger.info("Initializing GUI...")
        app = MLSPhotoProcessorGUI(
            processor_func=process_folder,
            parcel_matcher=parcel_matcher,
            classifier=classifier
        )

        logger.info("Starting GUI main loop...")
        app.run()

        # ---- Session end ----
        SESSION_END_TIME = time.time()
        duration_seconds = int(SESSION_END_TIME - SESSION_START_TIME)
        logger.info(
            f"SESSION_END id={SESSION_ID} duration_seconds={duration_seconds}"
        )

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()