"""Main application entry point for MLS Photo Processor."""
import logging
import sys
from pathlib import Path

from matcher import ParcelMatcher
from classifier import ImageClassifier
from processor import process_folder
from gui import MLSPhotoProcessorGUI

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
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

