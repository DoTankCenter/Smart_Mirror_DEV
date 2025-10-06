import cv2
import numpy as np
from typing import List, Dict, Tuple
import base64
from ultralytics import YOLO
from sklearn.cluster import KMeans
from skimage import color as skcolor
from filterpy.kalman import KalmanFilter
import uuid

class GarmentSegmenter:
    """YOLOv8-seg based garment instance segmentation"""

    # DeepFashion2 / Fashion category mapping
    CATEGORY_MAP = {
        'short_sleeve_top': 'top',
        'long_sleeve_top': 'top',
        'short_sleeve_outwear': 'outerwear',
        'long_sleeve_outwear': 'outerwear',
        'vest': 'top',
        'sling': 'top',
        'shorts': 'bottom',
        'trousers': 'bottom',
        'skirt': 'bottom',
        'short_sleeve_dress': 'dress',
        'long_sleeve_dress': 'dress',
        'vest_dress': 'dress',
        'sling_dress': 'dress',
        'shoe': 'shoes',
        'shoes': 'shoes',
    }

    def __init__(self, model_path: str = 'yolov8n-seg.pt', conf_threshold: float = 0.5):
        """
        Initialize YOLOv8 segmentation model

        Args:
            model_path: Path to YOLOv8-seg model (use DeepFashion2 fine-tuned if available)
            conf_threshold: Confidence threshold for detections
        """
        print(f"Loading YOLOv8-seg model: {model_path}")
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

        # Person tracking state
        self.person_trackers = {}  # person_id -> {bbox, kalman_filter, last_seen, garments}
        self.next_person_id = 0
        self.garment_id_counter = 0

        # Temporal stability (EMA filter for smooth color/position)
        self.ema_alpha = 0.3  # Lower = more smoothing

        # Garment tracking (prevent flicker)
        self.garment_cache = {}  # garment_key -> {id, stable_frames, last_data}
        self.stability_threshold = 3  # Frames before garment is "confirmed"

        print("YOLOv8-seg garment segmenter initialized")

    def segment_garments(self, image: np.ndarray) -> List[Dict]:
        """
        Segment garments from image using YOLOv8

        Returns:
            List of garment dictionaries with:
                - id: unique stable garment ID
                - person_id: which person this belongs to
                - category: 'top', 'bottom', 'shoes', 'outerwear', 'dress'
                - fine_category: original detailed category
                - bbox: [x, y, w, h]
                - color: dominant color [r, g, b]
                - color_lab: LAB color values
                - color_hex: hex color string
                - confidence: detection confidence
                - features: feature vector for similarity search
                - thumbnail: base64 encoded thumbnail
        """
        results = []

        # Run YOLOv8 inference
        predictions = self.model(image, conf=self.conf_threshold, verbose=False)

        if len(predictions) == 0 or predictions[0].masks is None:
            # Clean up old trackers
            self._cleanup_trackers()
            return results

        pred = predictions[0]

        # Group detections by person (spatial clustering)
        person_groups = self._group_by_person(pred, image.shape)

        # Process each person's garments
        for person_id, garment_detections in person_groups.items():
            for det in garment_detections:
                garment = self._process_garment(image, det, person_id)
                if garment:
                    results.append(garment)

        # Clean up old cached garments
        self._cleanup_garment_cache()

        return results

    def _group_by_person(self, pred, image_shape: Tuple[int, int, int]) -> Dict[int, List]:
        """Group garment detections by person using spatial clustering"""
        if pred.boxes is None or len(pred.boxes) == 0:
            return {}

        detections = []
        for i in range(len(pred.boxes)):
            box = pred.boxes[i]
            mask = pred.masks[i] if pred.masks is not None else None
            cls_id = int(box.cls[0])

            detections.append({
                'bbox': box.xyxy[0].cpu().numpy(),
                'conf': float(box.conf[0]),
                'class': self.model.names[cls_id] if hasattr(self.model, 'names') else str(cls_id),
                'mask': mask.data[0].cpu().numpy() if mask is not None else None
            })

        # Simple spatial clustering: compute center of each garment
        # Group garments that are close together vertically and horizontally
        person_groups = {}

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # Find closest existing person
            assigned = False
            for pid, tracker in self.person_trackers.items():
                tx, ty, tw, th = tracker['bbox']
                tcx = tx + tw / 2
                tcy = ty + th / 2

                # Distance threshold (relative to image size)
                dist_threshold = min(image_shape[0], image_shape[1]) * 0.3
                dist = np.sqrt((center_x - tcx)**2 + (center_y - tcy)**2)

                if dist < dist_threshold:
                    if pid not in person_groups:
                        person_groups[pid] = []
                    person_groups[pid].append(det)
                    assigned = True
                    break

            # Create new person if not assigned
            if not assigned:
                new_pid = self._create_person_tracker(det['bbox'])
                person_groups[new_pid] = [det]

        return person_groups

    def _create_person_tracker(self, bbox: np.ndarray) -> int:
        """Create a new person tracker"""
        person_id = self.next_person_id
        self.next_person_id += 1

        x1, y1, x2, y2 = bbox

        self.person_trackers[person_id] = {
            'bbox': [x1, y1, x2 - x1, y2 - y1],
            'last_seen': 0,
            'garments': []
        }

        return person_id

    def _process_garment(self, image: np.ndarray, detection: Dict, person_id: int) -> Dict:
        """Process a single garment detection"""
        x1, y1, x2, y2 = detection['bbox']
        mask = detection['mask']
        fine_category = detection['class']
        confidence = detection['conf']

        # Map to coarse category
        category = self.CATEGORY_MAP.get(fine_category.lower(), 'top')

        # Create garment key for tracking
        garment_key = f"{person_id}_{category}"

        # Extract mask at full resolution
        if mask.shape != image.shape[:2]:
            mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)

        mask_binary = (mask > 0.5).astype(np.uint8)

        # Extract masked region
        garment_region = cv2.bitwise_and(image, image, mask=mask_binary)

        # Get bounding box from mask
        contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        if w * h < 500:  # Too small
            return None

        # Extract crop
        crop = garment_region[y:y+h, x:x+w]
        crop_mask = mask_binary[y:y+h, x:x+w]

        # Extract dominant color in LAB space (more perceptually accurate)
        dominant_color_rgb, dominant_color_lab = self._extract_dominant_color_lab(crop, crop_mask)
        color_hex = '#{:02x}{:02x}{:02x}'.format(*dominant_color_rgb)

        # Apply EMA smoothing if garment was seen before
        if garment_key in self.garment_cache:
            cached = self.garment_cache[garment_key]
            cached['stable_frames'] += 1

            # Smooth color
            prev_lab = cached['last_data']['color_lab']
            dominant_color_lab = [
                self.ema_alpha * dominant_color_lab[i] + (1 - self.ema_alpha) * prev_lab[i]
                for i in range(3)
            ]
            # Convert back to RGB
            lab_array = np.array([[dominant_color_lab]], dtype=np.float32)
            rgb_array = skcolor.lab2rgb(lab_array) * 255
            dominant_color_rgb = rgb_array[0, 0].astype(int).tolist()
            color_hex = '#{:02x}{:02x}{:02x}'.format(*dominant_color_rgb)

            garment_id = cached['id']
        else:
            # New garment
            garment_id = self.garment_id_counter
            self.garment_id_counter += 1
            self.garment_cache[garment_key] = {
                'id': garment_id,
                'stable_frames': 1,
                'last_data': {}
            }

        # Create thumbnail (masked crop on grey background)
        thumbnail = self._create_thumbnail(crop, crop_mask)

        # Extract features (color histogram + simple texture)
        features = self._extract_features(crop, crop_mask, dominant_color_lab)

        # Store data for EMA next frame
        self.garment_cache[garment_key]['last_data'] = {
            'color_lab': dominant_color_lab,
            'bbox': [x, y, w, h]
        }

        return {
            'id': garment_id,
            'person_id': person_id,
            'category': category,
            'fine_category': fine_category,
            'bbox': [int(x), int(y), int(w), int(h)],
            'color': dominant_color_rgb,
            'color_lab': dominant_color_lab,
            'color_hex': color_hex,
            'confidence': float(confidence),
            'features': features,
            'thumbnail': thumbnail,
            'stable': self.garment_cache[garment_key]['stable_frames'] >= self.stability_threshold
        }

    def _extract_dominant_color_lab(self, image: np.ndarray, mask: np.ndarray, k: int = 3) -> Tuple[List[int], List[float]]:
        """Extract dominant color using K-means in LAB color space"""
        # Get masked pixels
        pixels = image[mask > 0]

        if len(pixels) < 10:
            return [128, 128, 128], [50.0, 0.0, 0.0]

        # Convert to LAB
        pixels_rgb = pixels.reshape(-1, 3).astype(np.float32) / 255.0

        # Create a dummy image for conversion
        dummy_image = pixels_rgb.reshape(1, -1, 3)
        lab_pixels = skcolor.rgb2lab(dummy_image).reshape(-1, 3)

        # K-means clustering
        if len(lab_pixels) > k:
            kmeans = KMeans(n_clusters=min(k, len(lab_pixels)), random_state=0, n_init=10)
            kmeans.fit(lab_pixels)

            # Get largest cluster
            labels = kmeans.labels_
            counts = np.bincount(labels)
            dominant_idx = np.argmax(counts)
            dominant_lab = kmeans.cluster_centers_[dominant_idx]
        else:
            dominant_lab = np.median(lab_pixels, axis=0)

        # Convert back to RGB
        lab_array = np.array([[dominant_lab]], dtype=np.float32)
        rgb_array = skcolor.lab2rgb(lab_array) * 255
        dominant_rgb = rgb_array[0, 0].astype(int).tolist()

        return dominant_rgb, dominant_lab.tolist()

    def _create_thumbnail(self, image: np.ndarray, mask: np.ndarray, size: int = 128) -> str:
        """Create thumbnail with garment on grey background"""
        # Create grey background
        grey_bg = np.full_like(image, 180)

        # Composite garment on grey
        mask_3ch = cv2.merge([mask, mask, mask])
        composite = np.where(mask_3ch > 0, image, grey_bg)

        # Resize
        h, w = composite.shape[:2]
        if h > w:
            new_h = size
            new_w = int(w * size / h)
        else:
            new_w = size
            new_h = int(h * size / w)

        resized = cv2.resize(composite, (new_w, new_h))

        # Pad to square
        canvas = np.full((size, size, 3), 180, dtype=np.uint8)
        y_offset = (size - new_h) // 2
        x_offset = (size - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

        # Encode to base64
        _, buffer = cv2.imencode('.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
        thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')

        return f"data:image/jpeg;base64,{thumbnail_b64}"

    def _extract_features(self, image: np.ndarray, mask: np.ndarray, color_lab: List[float]) -> List[float]:
        """Extract feature vector for similarity search"""
        features = []

        # LAB color features (already have dominant color)
        features.extend(color_lab)

        # Color histogram in LAB
        lab_image = skcolor.rgb2lab(image.astype(np.float32) / 255.0)

        for channel in range(3):
            hist = cv2.calcHist([lab_image], [channel], mask, [16],
                               [0, 100] if channel == 0 else [-127, 127])
            hist = cv2.normalize(hist, hist).flatten()
            features.extend(hist.tolist())

        # Simple texture feature (edge density)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        masked_edges = cv2.bitwise_and(edges, edges, mask=mask)
        edge_density = np.sum(masked_edges > 0) / (np.sum(mask > 0) + 1e-6)
        features.append(edge_density)

        return features

    def _cleanup_trackers(self):
        """Remove old person trackers"""
        to_remove = []
        for pid, tracker in self.person_trackers.items():
            tracker['last_seen'] += 1
            if tracker['last_seen'] > 30:  # ~1 second at 30fps
                to_remove.append(pid)

        for pid in to_remove:
            del self.person_trackers[pid]

    def _cleanup_garment_cache(self):
        """Remove old garment cache entries"""
        # Keep only recent garments
        active_keys = set()
        for tracker in self.person_trackers.values():
            for g in tracker.get('garments', []):
                active_keys.add(f"{g['person_id']}_{g['category']}")

        to_remove = []
        for key in self.garment_cache.keys():
            if key not in active_keys:
                to_remove.append(key)

        for key in to_remove:
            del self.garment_cache[key]
