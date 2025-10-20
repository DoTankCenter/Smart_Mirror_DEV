"""
Cloth segmentation using U2NET model
This is a simpler alternative to YOLO that works better for clothing detection
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
import base64
from sklearn.cluster import KMeans
from skimage import color as skcolor

# Install: pip install cloth-segmentation
try:
    from cloths_segmentation.pre_trained_models import create_model
    CLOTH_SEG_AVAILABLE = True
except ImportError:
    print("WARNING: cloth-segmentation not installed. Run: pip install cloth-segmentation")
    CLOTH_SEG_AVAILABLE = False


class ClothSegmenter:
    """Cloth segmentation using U2NET pre-trained model"""

    def __init__(self):
        """Initialize cloth segmentation model"""
        if not CLOTH_SEG_AVAILABLE:
            raise ImportError("cloth-segmentation is not installed")

        print("Loading U2NET cloth segmentation model...")
        self.model = create_model("u2net")
        print("Cloth segmentation model loaded successfully")

        # Garment tracking
        self.garment_id_counter = 0
        self.garment_cache = {}  # garment_key -> {id, stable_frames, last_data}
        self.stability_threshold = 3  # Frames before confirmed
        self.ema_alpha = 0.3  # Smoothing factor

    def segment_garments(self, image: np.ndarray) -> List[Dict]:
        """
        Segment garments from image

        Returns:
            List of garment dictionaries
        """
        results = []

        # Get cloth mask
        print("DEBUG: Running cloth segmentation...")
        cloth_mask = self.model(image)

        # cloth_mask is a binary mask where 1 = clothing, 0 = background
        if cloth_mask is None or cloth_mask.sum() == 0:
            print("DEBUG: No clothing detected in frame")
            self._cleanup_garment_cache()
            return results

        print(f"DEBUG: Found {cloth_mask.sum()} clothing pixels")

        # Find contours to separate different garment pieces
        contours, _ = cv2.findContours(
            (cloth_mask * 255).astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        print(f"DEBUG: Found {len(contours)} clothing contours")

        # Process each contour as a potential garment
        person_id = 0  # Single person for now

        for idx, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            # Skip very small regions
            if area < 5000:  # Minimum area threshold
                print(f"DEBUG: Skipping small contour {idx} (area: {area})")
                continue

            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)

            # Determine if it's upper or lower garment based on position
            img_height = image.shape[0]
            center_y = y + h / 2

            if center_y < img_height * 0.6:
                category = 'top'
                fine_category = 'shirt'
            else:
                category = 'bottom'
                fine_category = 'pants'

            # Create mask for this contour
            garment_mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.drawContours(garment_mask, [contour], -1, 1, -1)

            # Process garment
            garment = self._process_garment(
                image, garment_mask, category, fine_category,
                [x, y, w, h], person_id
            )

            if garment:
                results.append(garment)
                print(f"DEBUG: Added {category} garment (stable: {garment['stable']})")

        self._cleanup_garment_cache()
        print(f"DEBUG: Returning {len(results)} garments")

        return results

    def _process_garment(self, image: np.ndarray, mask: np.ndarray,
                        category: str, fine_category: str,
                        bbox: List[int], person_id: int) -> Dict:
        """Process a single garment"""
        x, y, w, h = bbox

        # Create garment key for tracking
        garment_key = f"{person_id}_{category}"

        # Extract masked region
        garment_region = cv2.bitwise_and(image, image, mask=mask)

        # Get crop
        crop = garment_region[y:y+h, x:x+w]
        crop_mask = mask[y:y+h, x:x+w]

        if crop_mask.sum() < 100:  # Too small
            return None

        # Extract dominant color
        dominant_color_rgb, dominant_color_lab = self._extract_dominant_color_lab(crop, crop_mask)
        color_hex = '#{:02x}{:02x}{:02x}'.format(*dominant_color_rgb)

        # Apply EMA smoothing if seen before
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

        # Create thumbnail
        thumbnail = self._create_thumbnail(crop, crop_mask)

        # Extract features
        features = self._extract_features(crop, crop_mask, dominant_color_lab)

        # Store data for next frame
        self.garment_cache[garment_key]['last_data'] = {
            'color_lab': dominant_color_lab,
            'bbox': bbox
        }

        is_stable = self.garment_cache[garment_key]['stable_frames'] >= self.stability_threshold

        return {
            'id': garment_id,
            'person_id': person_id,
            'category': category,
            'fine_category': fine_category,
            'bbox': [int(x), int(y), int(w), int(h)],
            'color': dominant_color_rgb,
            'color_lab': dominant_color_lab,
            'color_hex': color_hex,
            'confidence': 0.95,  # U2NET is quite confident
            'features': features,
            'thumbnail': thumbnail,
            'stable': is_stable
        }

    def _extract_dominant_color_lab(self, image: np.ndarray, mask: np.ndarray, k: int = 3) -> Tuple[List[int], List[float]]:
        """Extract dominant color using K-means in LAB color space"""
        pixels = image[mask > 0]

        if len(pixels) < 10:
            return [128, 128, 128], [50.0, 0.0, 0.0]

        # Convert to LAB
        pixels_rgb = pixels.reshape(-1, 3).astype(np.float32) / 255.0
        dummy_image = pixels_rgb.reshape(1, -1, 3)
        lab_pixels = skcolor.rgb2lab(dummy_image).reshape(-1, 3)

        # K-means clustering
        if len(lab_pixels) > k:
            kmeans = KMeans(n_clusters=min(k, len(lab_pixels)), random_state=0, n_init=10)
            kmeans.fit(lab_pixels)
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
        grey_bg = np.full_like(image, 180)
        mask_3ch = cv2.merge([mask, mask, mask])
        composite = np.where(mask_3ch > 0, image, grey_bg)

        h, w = composite.shape[:2]
        if h > w:
            new_h = size
            new_w = int(w * size / h)
        else:
            new_w = size
            new_h = int(h * size / w)

        resized = cv2.resize(composite, (new_w, new_h))

        canvas = np.full((size, size, 3), 180, dtype=np.uint8)
        y_offset = (size - new_h) // 2
        x_offset = (size - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

        _, buffer = cv2.imencode('.jpg', canvas, [cv2.IMWRITE_JPEG_QUALITY, 85])
        thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')

        return f"data:image/jpeg;base64,{thumbnail_b64}"

    def _extract_features(self, image: np.ndarray, mask: np.ndarray, color_lab: List[float]) -> List[float]:
        """Extract feature vector for similarity search"""
        features = []
        features.extend(color_lab)

        # Color histogram in LAB
        lab_image = skcolor.rgb2lab(image.astype(np.float32) / 255.0)

        for channel in range(3):
            hist = cv2.calcHist([lab_image], [channel], mask, [16],
                               [0, 100] if channel == 0 else [-127, 127])
            hist = cv2.normalize(hist, hist).flatten()
            features.extend(hist.tolist())

        # Texture feature
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        masked_edges = cv2.bitwise_and(edges, edges, mask=mask)
        edge_density = np.sum(masked_edges > 0) / (np.sum(mask > 0) + 1e-6)
        features.append(edge_density)

        return features

    def _cleanup_garment_cache(self):
        """Remove old garment cache entries"""
        # Keep only recent garments (last 30 frames)
        to_remove = []
        for key, cache in self.garment_cache.items():
            if cache.get('frames_since_seen', 0) > 30:
                to_remove.append(key)
            else:
                cache['frames_since_seen'] = cache.get('frames_since_seen', 0) + 1

        for key in to_remove:
            del self.garment_cache[key]
