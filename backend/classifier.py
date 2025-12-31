"""Three-layer image classification: Hard rules → Heuristics → Hugging Face fallback."""
import logging
from typing import Optional, List, Tuple, Dict
from PIL import Image
import torch
import numpy as np

logger = logging.getLogger(__name__)

# Try to import CLIP for object detection and classification
try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("CLIP not available. Classification will be limited.")


class ImageClassifier:
    """Three-layer image classifier: Hard rules → Heuristics → Hugging Face fallback."""
    
    # Final allowed classifications (ALL CAPS ONLY)
    CANONICAL_LABELS = {
        'KITCHEN',
        'LIVING ROOM',
        'BEDROOM',
        'OFFICE',
        'DINING ROOM',
        'LAUNDRY ROOM',
        'DECK',
        'EXTERIOR',
        'BATHROOM',
        'OTHER'
    }
    
    # Minimum confidence threshold for object detection
    OBJECT_DETECTION_THRESHOLD = 0.6
    
    # Confidence threshold for Hugging Face classifier (Layer 3)
    HF_CLASSIFIER_THRESHOLD = 0.65
    
    def __init__(self):
        """Initialize rule-based classifier with CLIP for object detection."""
        self.clip_processor = None
        self.clip_model = None
        self._load_clip_model()
    
    def _load_clip_model(self):
        """Load CLIP model for object detection only."""
        if not CLIP_AVAILABLE:
            logger.warning("CLIP not available. Classification will be limited.")
            return
        
        try:
            logger.info("Loading CLIP model for object detection...")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model.eval()
            logger.info("CLIP model loaded successfully for object detection")
        except Exception as e:
            logger.error(f"Error loading CLIP model: {e}")
            logger.warning("Object detection will be unavailable. All images will be classified as OTHER.")
            self.clip_processor = None
            self.clip_model = None
    
    
    def _load_image_from_path(self, image_path: str) -> Optional[Image.Image]:
        """Load image from local file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            PIL Image or None if failed
        """
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
        except Exception as e:
            logger.error(f"Error loading image from {image_path}: {e}")
            return None
    
    def _detect_objects(self, image: Image.Image) -> Dict[str, float]:
        """
        Detect objects in image using CLIP.
        Returns dictionary of object -> confidence score.
        
        Args:
            image: PIL Image
            
        Returns:
            Dictionary mapping object names to confidence scores
        """
        if not self.clip_model or not self.clip_processor:
            return {}
        
        # Objects to detect for rule-based classification
        object_queries = [
            # Bathroom
            'toilet', 'bathtub', 'shower', 'bathroom',
            # Bedroom
            'bed', 'mattress', 'bedroom bed',
            # Kitchen
            'refrigerator', 'fridge', 'stove', 'oven', 'kitchen sink', 'sink', 'kitchen cabinets', 'cabinet',
            # Laundry
            'washing machine', 'dryer', 'washer',
            'detergent bottle', 'laundry detergent', 'utility sink', 'laundry basket', 'dryer vent', 'lint trap',
            # Office
            'desk', 'office desk', 'chair', 'office chair', 'computer', 'laptop',
            # Living room
            'couch', 'sofa', 'television', 'tv', 'tv screen', 'fireplace',
            # Dining room
            'dining table', 'table', 'dining room table',
            # Deck/Outdoor
            'outdoor furniture', 'patio furniture', 'outdoor chair', 'outdoor table', 'railing', 'deck railing',
            'trees', 'sky', 'siding', 'house siding',
            # General
            'outdoor', 'outside', 'indoor', 'inside'
        ]
        
        try:
            # Process image and text queries
            inputs = self.clip_processor(
                text=object_queries,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            # Run inference
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
            
            # Get similarity scores
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            # Build detection dictionary
            detections = {}
            for i, query in enumerate(object_queries):
                confidence = float(probs[0][i].item())
                if confidence >= self.OBJECT_DETECTION_THRESHOLD:
                    detections[query] = confidence
            
            return detections
            
        except Exception as e:
            logger.error(f"Error in object detection: {e}")
            return {}
    
    def _is_outdoor(self, image: Image.Image, detections: Dict[str, float]) -> bool:
        """
        Determine if image is outdoor using heuristics and detections.
        
        Args:
            image: PIL Image
            detections: Dictionary of detected objects
            
        Returns:
            True if image appears to be outdoor
        """
        # Check detections first
        outdoor_keywords = ['outdoor', 'outside']
        if any(keyword in detections for keyword in outdoor_keywords):
            return True
        
        # Use pixel-based heuristic
        try:
            img_array = np.array(image)
            
            # Check for sky (bright blue/white pixels in top portion)
            top_portion = img_array[:img_array.shape[0]//3, :]
            blue_mask = (top_portion[:, :, 2] > 150) & (top_portion[:, :, 1] > 100) & (top_portion[:, :, 0] < 150)
            sky_ratio = np.sum(blue_mask) / (top_portion.shape[0] * top_portion.shape[1])
            
            # Check for green (grass) in bottom portion
            bottom_portion = img_array[2*img_array.shape[0]//3:, :]
            green_mask = (bottom_portion[:, :, 1] > bottom_portion[:, :, 0]) & (bottom_portion[:, :, 1] > bottom_portion[:, :, 2])
            grass_ratio = np.sum(green_mask) / (bottom_portion.shape[0] * bottom_portion.shape[1])
            
            # High brightness variance suggests outdoor lighting
            gray = np.mean(img_array, axis=2)
            brightness_variance = np.var(gray)
            
            if sky_ratio > 0.2 or grass_ratio > 0.3 or brightness_variance > 5000:
                return True
                
        except Exception as e:
            logger.debug(f"Error in outdoor detection: {e}")
        
        return False
    
    def _apply_layer1_hard_rules(self, image: Image.Image, detections: Dict[str, float]) -> Optional[Tuple[str, str]]:
        """
        Layer 1: Hard rules that override all other logic.
        
        Args:
            image: PIL Image
            detections: Dictionary of detected objects with confidence scores
            
        Returns:
            Tuple of (label, rule_description) if a hard rule matches, None otherwise
        """
        # Helper function to check detections
        def has_object(keywords: List[str]) -> bool:
            return any(kw in detections for kw in keywords)
        
        # Hard Rule 1: BATHROOM - If toilet, bathtub, or shower is detected
        if has_object(['toilet', 'bathtub', 'shower', 'bathroom']):
            return ('BATHROOM', 'Layer 1 Hard Rule: Bathroom fixture detected')
        
        # Hard Rule 2: LAUNDRY ROOM - Restrictive rule to reduce false positives
        # Must have: (both washer AND dryer) OR (at least one appliance AND laundry-specific indicator)
        has_washer = has_object(['washing machine', 'washer'])
        has_dryer = has_object(['dryer'])
        has_laundry_indicator = has_object([
            'detergent bottle', 'laundry detergent',
            'utility sink',
            'laundry basket',
            'dryer vent', 'lint trap'
        ])
        
        # Condition 1: Both washer AND dryer visible
        if has_washer and has_dryer:
            return ('LAUNDRY ROOM', 'Layer 1 Hard Rule: Both washer and dryer detected')
        
        # Condition 2: At least one appliance AND laundry-specific indicator
        if (has_washer or has_dryer) and has_laundry_indicator:
            return ('LAUNDRY ROOM', 'Layer 1 Hard Rule: Laundry appliance with laundry-specific indicator')
        
        # If conditions not met, do NOT classify as LAUNDRY ROOM (fall through to other rules)
        
        # Hard Rule 3: BEDROOM - If bed or mattress is detected
        if has_object(['bed', 'mattress', 'bedroom bed']):
            return ('BEDROOM', 'Layer 1 Hard Rule: Bed detected')
        
        # Hard Rule 4: OFFICE - If desk AND (chair OR computer) is detected
        has_desk = has_object(['desk', 'office desk'])
        has_chair = has_object(['chair', 'office chair'])
        has_computer = has_object(['computer', 'laptop'])
        
        if has_desk and (has_chair or has_computer):
            return ('OFFICE', 'Layer 1 Hard Rule: Desk with chair or computer detected')
        
        # Hard Rule 5: DECK - If outdoor scene AND (outdoor furniture OR railing) AND (trees/sky/siding)
        is_outdoor = self._is_outdoor(image, detections)
        has_outdoor_furniture = has_object(['outdoor furniture', 'patio furniture', 'outdoor chair', 'outdoor table'])
        has_railing = has_object(['railing', 'deck railing'])
        has_outdoor_features = has_object(['trees', 'sky', 'siding', 'house siding'])
        
        if is_outdoor and (has_outdoor_furniture or has_railing) and has_outdoor_features:
            return ('DECK', 'Layer 1 Hard Rule: Outdoor scene with furniture/railing and trees/sky/siding')
        
        # Hard Rule 6: EXTERIOR - If outdoor scene without furniture
        if is_outdoor and not has_object(['outdoor furniture', 'patio furniture', 'outdoor chair', 'outdoor table', 'chair', 'table', 'couch', 'sofa', 'railing']):
            return ('EXTERIOR', 'Layer 1 Hard Rule: Outdoor scene without furniture')
        
        return None
    
    def _apply_layer2_heuristic_rules(self, image: Image.Image, detections: Dict[str, float]) -> Optional[Tuple[str, str]]:
        """
        Layer 2: Heuristic rules (applied if no hard rules match).
        
        Args:
            image: PIL Image
            detections: Dictionary of detected objects with confidence scores
            
        Returns:
            Tuple of (label, rule_description) if a heuristic rule matches, None otherwise
        """
        # Helper functions
        def has_object(keywords: List[str]) -> bool:
            return any(kw in detections for kw in keywords)
        
        def has_any_object(keyword_lists: List[List[str]]) -> bool:
            return any(any(kw in detections for kw in keywords) for keywords in keyword_lists)
        
        # Heuristic Rule 1: KITCHEN - sink + refrigerator OR stove + cabinets
        has_sink = has_object(['kitchen sink', 'sink'])
        has_refrigerator = has_object(['refrigerator', 'fridge'])
        has_stove = has_object(['stove', 'oven'])
        has_cabinets = has_object(['kitchen cabinets', 'cabinet'])
        
        if (has_sink and has_refrigerator) or (has_stove and has_cabinets):
            return ('KITCHEN', 'Layer 2 Heuristic: Kitchen appliances detected (sink+fridge OR stove+cabinets)')
        
        # Heuristic Rule 2: DINING ROOM - table present, no bed, no appliances
        has_table = has_object(['dining table', 'table', 'dining room table'])
        has_bed = has_object(['bed', 'mattress'])
        has_appliances = has_any_object([
            ['refrigerator', 'fridge'],
            ['stove', 'oven'],
            ['washing machine', 'dryer']
        ])
        
        if has_table and not has_bed and not has_appliances:
            return ('DINING ROOM', 'Layer 2 Heuristic: Table detected, no bed or appliances')
        
        # Heuristic Rule 3: LIVING ROOM - couch/sofa AND (TV OR fireplace)
        has_couch = has_object(['couch', 'sofa'])
        has_tv = has_object(['television', 'tv', 'tv screen'])
        has_fireplace = has_object(['fireplace'])
        
        if has_couch and (has_tv or has_fireplace):
            return ('LIVING ROOM', 'Layer 2 Heuristic: Couch/sofa with TV or fireplace')
        
        return None
    
    def _apply_layer3_hf_classifier(self, image: Image.Image) -> Optional[Tuple[str, str]]:
        """
        Layer 3: Hugging Face classifier (fallback only).
        Uses CLIP zero-shot classification to classify room types.
        
        Args:
            image: PIL Image
            
        Returns:
            Tuple of (label, confidence_score) if confidence >= threshold, None otherwise
        """
        if not self.clip_model or not self.clip_processor:
            return None
        
        # Room type labels for zero-shot classification
        room_labels = [
            'kitchen',
            'living room',
            'bedroom',
            'office',
            'dining room',
            'laundry room',
            'deck',
            'exterior',
            'bathroom'
        ]
        
        try:
            # Process image and text labels
            inputs = self.clip_processor(
                text=room_labels,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            # Run inference
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
            
            # Get similarity scores
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            # Find top prediction
            top_idx = torch.argmax(probs, dim=1).item()
            top_confidence = float(probs[0][top_idx].item())
            top_label = room_labels[top_idx]
            
            # Map to canonical label
            label_mapping = {
                'kitchen': 'KITCHEN',
                'living room': 'LIVING ROOM',
                'bedroom': 'BEDROOM',
                'office': 'OFFICE',
                'dining room': 'DINING ROOM',
                'laundry room': 'LAUNDRY ROOM',
                'deck': 'DECK',
                'exterior': 'EXTERIOR',
                'bathroom': 'BATHROOM'
            }
            
            canonical_label = label_mapping.get(top_label, 'OTHER')
            
            # Only return if confidence meets threshold
            if top_confidence >= self.HF_CLASSIFIER_THRESHOLD:
                return (canonical_label, f'Layer 3 HF Classifier: {top_label} (confidence: {top_confidence:.3f})')
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Hugging Face classifier: {e}")
            return None
    
    def classify_image(self, image_path: str) -> str:
        """
        Classify image using three-layer approach:
        1. Layer 1: Hard rules (override all)
        2. Layer 2: Heuristic rules
        3. Layer 3: Hugging Face classifier (fallback)
        
        Args:
            image_path: Path to local image file
            
        Returns:
            Classification label (ALL CAPS)
        """
        try:
            # Load image
            image = self._load_image_from_path(image_path)
            
            if not image:
                logger.warning(f"Could not load image: {image_path}")
                return 'OTHER'
            
            # Step 1: Detect objects using CLIP
            detections = self._detect_objects(image)
            
            # Log detected objects and confidence scores
            if detections:
                detection_str = ", ".join([f"{obj}({conf:.2f})" for obj, conf in sorted(detections.items(), key=lambda x: x[1], reverse=True)])
                logger.info(f"Detected objects: {detection_str}")
            else:
                logger.info("No objects detected above threshold")
            
            # Step 2: Apply Layer 1 - Hard rules (override all)
            layer1_result = self._apply_layer1_hard_rules(image, detections)
            if layer1_result:
                final_label, rule_description = layer1_result
                logger.info(f"Layer 1 (Hard Rule): {rule_description}")
                logger.info(f"Final classification: {final_label}")
                if final_label not in self.CANONICAL_LABELS:
                    logger.warning(f"Label {final_label} not in allowed set, defaulting to OTHER")
                    return 'OTHER'
                return final_label
            
            # Step 3: Apply Layer 2 - Heuristic rules
            layer2_result = self._apply_layer2_heuristic_rules(image, detections)
            if layer2_result:
                final_label, rule_description = layer2_result
                logger.info(f"Layer 2 (Heuristic): {rule_description}")
                logger.info(f"Final classification: {final_label}")
                if final_label not in self.CANONICAL_LABELS:
                    logger.warning(f"Label {final_label} not in allowed set, defaulting to OTHER")
                    return 'OTHER'
                return final_label
            
            # Step 4: Apply Layer 3 - Hugging Face classifier (fallback)
            layer3_result = self._apply_layer3_hf_classifier(image)
            if layer3_result:
                final_label, rule_description = layer3_result
                logger.info(f"Layer 3 (HF Classifier): {rule_description}")
                logger.info(f"Final classification: {final_label}")
                if final_label not in self.CANONICAL_LABELS:
                    logger.warning(f"Label {final_label} not in allowed set, defaulting to OTHER")
                    return 'OTHER'
                return final_label
            
            # No rules matched and HF classifier below threshold
            logger.info("Layer 3: No rules matched and HF classifier below threshold")
            logger.info("Final classification: OTHER")
            return 'OTHER'
            
        except Exception as e:
            logger.error(f"Error classifying image {image_path}: {e}", exc_info=True)
            return 'OTHER'
    
    def classify_images(self, image_paths: List[str]) -> List[Tuple[str, str]]:
        """
        Classify multiple images from local file paths.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of tuples (file_path, classification)
        """
        results = []
        for image_path in image_paths:
            classification = self.classify_image(image_path)
            results.append((image_path, classification))
        return results
