import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Tuple
import base64

class GarmentSegmenter:
    """Segments people and their clothing from camera frames"""

    def __init__(self):
        # Initialize MediaPipe Selfie Segmentation
        self.mp_selfie_segmentation = mp.solutions.selfie_segmentation
        self.selfie_segmenter = self.mp_selfie_segmentation.SelfieSegmentation(
            model_selection=1  # 0 for general, 1 for landscape
        )

        # Initialize pose detection for person tracking
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=True,
            min_detection_confidence=0.5
        )

        self.person_tracker = {}
        self.next_person_id = 0
        self.garment_id_counter = 0

    def segment_garments(self, image: np.ndarray) -> List[Dict]:
        """
        Segment garments from an image

        Returns:
            List of garment dictionaries with:
                - id: unique garment ID
                - person_id: which person this garment belongs to
                - category: 'top', 'bottom', 'shoes', 'outerwear'
                - bbox: bounding box [x, y, w, h]
                - color: dominant color [r, g, b]
                - features: feature vector for similarity search
                - thumbnail: base64 encoded thumbnail
        """
        results = []

        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Run pose detection with segmentation
        pose_results = self.pose.process(rgb_image)

        if not pose_results.pose_landmarks:
            return results

        # Get segmentation mask
        segmentation_mask = pose_results.segmentation_mask

        if segmentation_mask is None:
            return results

        # Threshold the mask
        binary_mask = (segmentation_mask > 0.5).astype(np.uint8)

        # Find contours to separate multiple people
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for person_idx, contour in enumerate(contours):
            if cv2.contourArea(contour) < 5000:  # Filter small detections
                continue

            # Get bounding box for this person
            x, y, w, h = cv2.boundingRect(contour)

            # Assign person ID
            person_id = self._get_person_id(x, y, w, h)

            # Extract person region
            person_mask = np.zeros_like(binary_mask)
            cv2.drawContours(person_mask, [contour], -1, 1, -1)
            person_region = cv2.bitwise_and(rgb_image, rgb_image, mask=person_mask)

            # Segment into garment categories using landmarks
            landmarks = pose_results.pose_landmarks.landmark
            garments = self._classify_garments(person_region, person_mask, landmarks, person_id)

            results.extend(garments)

        return results

    def _get_person_id(self, x: int, y: int, w: int, h: int) -> int:
        """Track person across frames based on position"""
        center = (x + w // 2, y + h // 2)

        # Find closest tracked person
        min_dist = float('inf')
        person_id = None

        for pid, data in self.person_tracker.items():
            prev_center = data['center']
            dist = np.sqrt((center[0] - prev_center[0])**2 + (center[1] - prev_center[1])**2)
            if dist < min_dist and dist < 100:  # Max movement threshold
                min_dist = dist
                person_id = pid

        # Create new person if not found
        if person_id is None:
            person_id = self.next_person_id
            self.next_person_id += 1

        # Update tracker
        self.person_tracker[person_id] = {
            'center': center,
            'bbox': (x, y, w, h)
        }

        return person_id

    def _classify_garments(self, person_region: np.ndarray, mask: np.ndarray,
                          landmarks, person_id: int) -> List[Dict]:
        """Classify garments into categories based on body landmarks"""
        garments = []
        h, w = mask.shape

        # Define body regions using landmarks
        # Top: shoulders to hips
        # Bottom: hips to knees
        # Shoes: ankles to bottom

        try:
            # Get key landmark coordinates
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
            right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
            left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]
            right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE]
            left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
            right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]

            # Define regions
            shoulder_y = int(min(left_shoulder.y, right_shoulder.y) * h)
            hip_y = int(max(left_hip.y, right_hip.y) * h)
            knee_y = int(max(left_knee.y, right_knee.y) * h)
            ankle_y = int(max(left_ankle.y, right_ankle.y) * h)

            # Extract top garment (shirt/jacket)
            top_mask = mask.copy()
            top_mask[hip_y:, :] = 0
            top_garment = self._extract_garment(person_region, top_mask, 'top', person_id)
            if top_garment:
                garments.append(top_garment)

            # Extract bottom garment (pants)
            bottom_mask = mask.copy()
            bottom_mask[:hip_y, :] = 0
            bottom_mask[knee_y:, :] = 0
            bottom_garment = self._extract_garment(person_region, bottom_mask, 'bottom', person_id)
            if bottom_garment:
                garments.append(bottom_garment)

            # Extract shoes
            shoes_mask = mask.copy()
            shoes_mask[:ankle_y-20, :] = 0
            shoes_garment = self._extract_garment(person_region, shoes_mask, 'shoes', person_id)
            if shoes_garment:
                garments.append(shoes_garment)

        except Exception as e:
            print(f"Error classifying garments: {e}")

        return garments

    def _extract_garment(self, image: np.ndarray, mask: np.ndarray,
                        category: str, person_id: int) -> Dict:
        """Extract features from a garment region"""
        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)

        if cv2.contourArea(contour) < 1000:  # Too small
            return None

        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # Extract garment region
        garment_region = image[y:y+h, x:x+w]
        garment_mask = mask[y:y+h, x:x+w]

        # Calculate dominant color
        masked_region = cv2.bitwise_and(garment_region, garment_region, mask=garment_mask)
        pixels = masked_region[garment_mask > 0]

        if len(pixels) == 0:
            return None

        dominant_color = np.median(pixels, axis=0).astype(int).tolist()

        # Create thumbnail
        thumbnail = self._create_thumbnail(garment_region, garment_mask)

        # Create feature vector (simple color histogram + shape features)
        features = self._extract_features(garment_region, garment_mask)

        garment_id = self.garment_id_counter
        self.garment_id_counter += 1

        return {
            'id': garment_id,
            'person_id': person_id,
            'category': category,
            'bbox': [int(x), int(y), int(w), int(h)],
            'color': dominant_color,
            'features': features,
            'thumbnail': thumbnail
        }

    def _create_thumbnail(self, image: np.ndarray, mask: np.ndarray, size: int = 64) -> str:
        """Create a base64 encoded thumbnail of the garment"""
        # Resize
        resized = cv2.resize(image, (size, size))
        resized_mask = cv2.resize(mask, (size, size))

        # Apply mask with transparency
        bgra = cv2.cvtColor(resized, cv2.COLOR_RGB2BGRA)
        bgra[:, :, 3] = resized_mask * 255

        # Encode to base64
        _, buffer = cv2.imencode('.png', bgra)
        thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')

        return f"data:image/png;base64,{thumbnail_b64}"

    def _extract_features(self, image: np.ndarray, mask: np.ndarray) -> List[float]:
        """Extract feature vector for similarity search"""
        # Color histogram in HSV space
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

        hist_h = cv2.calcHist([hsv], [0], mask, [32], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], mask, [32], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], mask, [32], [0, 256])

        # Normalize
        hist_h = cv2.normalize(hist_h, hist_h).flatten()
        hist_s = cv2.normalize(hist_s, hist_s).flatten()
        hist_v = cv2.normalize(hist_v, hist_v).flatten()

        # Combine features
        features = np.concatenate([hist_h, hist_s, hist_v])

        return features.tolist()

    def __del__(self):
        self.pose.close()
        self.selfie_segmenter.close()
