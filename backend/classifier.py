"""
Scene-based image classification using CLIP.
Classifies MLS-style photos into room categories.
"""

import logging
from typing import List, Tuple
from PIL import Image
import torch

logger = logging.getLogger(__name__)

try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.error("CLIP is not available. Classification will fail.")


class ImageClassifier:
    """Scene-based room classifier using CLIP."""

    # Final allowed classifications
    CANONICAL_LABELS = {
        "KITCHEN",
        "LIVING ROOM",
        "BEDROOM",
        "OFFICE",
        "DINING ROOM",
        "DECK",
        "EXTERIOR",
        "BATHROOM",
        "OTHER"
    }

    # Mapping from CLIP scene labels → canonical labels
    LABEL_MAP = {
        "bathroom": "BATHROOM",
        "bedroom": "BEDROOM",
        "living room": "LIVING ROOM",
        "kitchen": "KITCHEN",
        "dining room": "DINING ROOM",
        "office": "OFFICE",
        "deck": "DECK",
        "exterior": "EXTERIOR"
    }

    # Confidence threshold for accepting CLIP classification
    CONFIDENCE_THRESHOLD = 0.35

    def __init__(self):
        self.clip_model = None
        self.clip_processor = None
        self._load_clip()

    def _load_clip(self):
        if not CLIP_AVAILABLE:
            return

        logger.info("Loading CLIP scene classification model...")
        self.clip_processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )
        self.clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32"
        )
        self.clip_model.eval()
        logger.info("CLIP loaded successfully")

    def _load_image(self, image_path: str) -> Image.Image | None:
        try:
            img = Image.open(image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            return img
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return None

    def _classify_scene(self, image: Image.Image) -> Tuple[str, float]:
        """
        Classify image scene using CLIP zero-shot labels.
        """

        labels = [
            "bathroom",
            "bedroom",
            "living room",
            "kitchen",
            "dining room",
            "office",
            "deck",
            "exterior"
        ]

        inputs = self.clip_processor(
            text=labels,
            images=image,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = self.clip_model(**inputs)

        probs = outputs.logits_per_image.softmax(dim=1)
        top_idx = probs.argmax(dim=1).item()

        return labels[top_idx], float(probs[0][top_idx])

    def classify_image(self, image_path: str) -> str:
        image = self._load_image(image_path)
        if not image:
            return "OTHER"

        scene, confidence = self._classify_scene(image)
        logger.info(f"CLIP scene → {scene.upper()} ({confidence:.2f})")

        if confidence < self.CONFIDENCE_THRESHOLD:
            return "OTHER"

        return self.LABEL_MAP.get(scene, "OTHER")

    def classify_images(self, image_paths: List[str]) -> List[Tuple[str, str]]:
        results = []
        for path in image_paths:
            label = self.classify_image(path)
            results.append((path, label))
        return results
