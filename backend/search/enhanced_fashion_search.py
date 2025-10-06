import torch
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
from PIL import Image
import faiss
import numpy as np
import os
from typing import List, Dict, Tuple, Optional
import pickle
import json
from skimage import color as skcolor
import cv2
import base64

class EnhancedFashionSearchEngine:
    """Enhanced semantic search with FashionCLIP, text fusion, and re-ranking"""

    def __init__(self, model_name: str = "patrickjohncyh/fashion-clip"):
        print(f"Loading FashionCLIP model: {model_name}")

        # Load FashionCLIP model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.tokenizer = CLIPTokenizer.from_pretrained(model_name)

        # Initialize FAISS index (HNSW for fast search on 34k images)
        self.dimension = 512  # CLIP embedding dimension

        # Use HNSW index for better performance with large datasets
        quantizer = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)  # 100 clusters
        self.index.nprobe = 10  # Search 10 nearest clusters
        self.is_trained = False

        # Store metadata for indexed images
        self.image_metadata = []  # List of dicts with path, description, category, etc.

        # Category weights for re-ranking
        self.category_boost = 1.2  # Boost score if category matches

        print(f"FashionCLIP loaded on {self.device}")

    def encode_image(self, image: np.ndarray, return_tensor: bool = False) -> np.ndarray:
        """Encode an image to a feature vector using FashionCLIP"""
        # Convert numpy array to PIL Image
        if isinstance(image, np.ndarray):
            if len(image.shape) == 2:  # Grayscale
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:  # RGBA
                image = image[:, :, :3]  # Drop alpha
            pil_image = Image.fromarray(image)
        else:
            pil_image = image

        # Process image
        inputs = self.processor(images=pil_image, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get embeddings
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            # Normalize for cosine similarity
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        if return_tensor:
            return image_features

        return image_features.cpu().numpy()[0]

    def encode_text(self, text: str, return_tensor: bool = False) -> np.ndarray:
        """Encode text description to feature vector"""
        inputs = self.tokenizer([text], padding=True, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        if return_tensor:
            return text_features

        return text_features.cpu().numpy()[0]

    def encode_multimodal(self, image: np.ndarray, text: str,
                         image_weight: float = 0.7) -> np.ndarray:
        """Combine image and text embeddings with weighted fusion"""
        img_embedding = self.encode_image(image)
        text_embedding = self.encode_text(text)

        # Weighted combination
        combined = image_weight * img_embedding + (1 - image_weight) * text_embedding

        # Re-normalize
        combined = combined / (np.linalg.norm(combined) + 1e-8)

        return combined

    def find_similar(self, features: List[float], garment_data: Optional[Dict] = None,
                    top_k: int = 10) -> List[Dict]:
        """
        Find similar items with re-ranking

        Args:
            features: Feature vector from garment
            garment_data: Additional data for re-ranking (category, color_lab, thumbnail)
            top_k: Number of results to return
        """
        if not self.is_trained or self.index.ntotal == 0:
            return []  # No items indexed yet

        # Convert features to numpy array
        query_embedding = np.array(features, dtype=np.float32).reshape(1, -1)

        # Normalize
        query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Search (get 3x candidates for re-ranking)
        search_k = min(top_k * 3, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, search_k)

        # Build initial results
        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.image_metadata):
                continue

            item = self.image_metadata[idx].copy()
            item['base_score'] = float(dist)  # Inner product (higher is better)
            candidates.append(item)

        # Re-rank if we have garment data
        if garment_data:
            candidates = self._rerank_results(candidates, garment_data)

        return candidates[:top_k]

    def _rerank_results(self, candidates: List[Dict], garment_data: Dict) -> List[Dict]:
        """Re-rank results by category match and color similarity"""
        garment_category = garment_data.get('category', '')
        garment_color_lab = garment_data.get('color_lab', None)

        for item in candidates:
            score = item['base_score']

            # Category boost
            item_category = item.get('category', '')
            if item_category and garment_category:
                if item_category.lower() == garment_category.lower():
                    score *= self.category_boost

            # Color similarity boost (LAB distance)
            if garment_color_lab and 'color_lab' in item:
                item_color_lab = item['color_lab']
                # Delta E (CIE76) - perceptual color difference
                delta_e = np.sqrt(
                    (garment_color_lab[0] - item_color_lab[0])**2 +
                    (garment_color_lab[1] - item_color_lab[1])**2 +
                    (garment_color_lab[2] - item_color_lab[2])**2
                )

                # Boost if similar color (delta_e < 30 is noticeable)
                if delta_e < 30:
                    color_similarity = 1.0 - (delta_e / 100.0)  # Normalize
                    score *= (1.0 + 0.3 * color_similarity)  # Up to 30% boost

                item['color_delta'] = float(delta_e)

            item['similarity'] = float(score)

        # Sort by final score
        candidates.sort(key=lambda x: x['similarity'], reverse=True)

        return candidates

    def index_directory(self, directory: str, metadata_file: Optional[str] = None) -> int:
        """
        Index a directory of images with optional metadata

        Args:
            directory: Path to image directory
            metadata_file: Optional JSON file with image metadata
                          Format: {"filename": {"description": "...", "category": "...", ...}}
        """
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist. Creating it...")
            os.makedirs(directory, exist_ok=True)
            return 0

        # Load metadata if provided
        metadata_map = {}
        if metadata_file and os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_map = json.load(f)
            print(f"Loaded metadata for {len(metadata_map)} items")

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        image_files = []

        for root, _, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1].lower() in image_extensions:
                    image_files.append(os.path.join(root, file))

        if not image_files:
            print(f"No images found in {directory}")
            return 0

        print(f"Indexing {len(image_files)} images...")

        embeddings = []
        metadata = []

        for idx, image_path in enumerate(image_files):
            try:
                filename = os.path.basename(image_path)

                # Load image
                image = Image.open(image_path).convert('RGB')
                image_np = np.array(image)

                # Get metadata for this image
                item_meta = metadata_map.get(filename, {})
                description = item_meta.get('description', '')

                # Encode with text fusion if description available
                if description:
                    embedding = self.encode_multimodal(image_np, description, image_weight=0.7)
                else:
                    embedding = self.encode_image(image_np)

                embeddings.append(embedding)

                # Extract color for re-ranking
                color_lab = self._extract_color_lab(image_np)

                # Store metadata
                metadata.append({
                    'id': idx,
                    'path': image_path,
                    'filename': filename,
                    'description': description,
                    'category': item_meta.get('category', ''),
                    'color_lab': color_lab,
                    **item_meta  # Include any other metadata fields
                })

                if (idx + 1) % 100 == 0:
                    print(f"Indexed {idx + 1}/{len(image_files)} images")

            except Exception as e:
                print(f"Error indexing {image_path}: {e}")

        # Train and add to FAISS index
        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)

            # Train index if not already trained
            if not self.is_trained:
                print("Training FAISS index...")
                self.index.train(embeddings_array)
                self.is_trained = True

            self.index.add(embeddings_array)
            self.image_metadata.extend(metadata)

            print(f"Successfully indexed {len(embeddings)} images")
            print(f"Total index size: {self.index.ntotal} items")

        return len(embeddings)

    def _extract_color_lab(self, image: np.ndarray) -> List[float]:
        """Extract dominant color in LAB space"""
        # Resize for speed
        small = cv2.resize(image, (100, 100))

        # Convert to LAB
        lab = skcolor.rgb2lab(small.astype(np.float32) / 255.0)

        # Get median color
        median_lab = np.median(lab.reshape(-1, 3), axis=0)

        return median_lab.tolist()

    def save_index(self, path: str = "fashion_index.pkl"):
        """Save the index and metadata to disk"""
        # Save FAISS index
        faiss.write_index(self.index, path + ".faiss")

        # Save metadata and training state
        with open(path, 'wb') as f:
            pickle.dump({
                'metadata': self.image_metadata,
                'is_trained': self.is_trained
            }, f)

        print(f"Index saved to {path}")

    def load_index(self, path: str = "fashion_index.pkl"):
        """Load the index and metadata from disk"""
        if not os.path.exists(path + ".faiss"):
            print(f"Index file {path}.faiss not found")
            return False

        # Load FAISS index
        self.index = faiss.read_index(path + ".faiss")

        # Load metadata
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.image_metadata = data['metadata']
            self.is_trained = data['is_trained']

        print(f"Index loaded: {self.index.ntotal} items")
        return True

    def add_image(self, image_path: str, metadata: Dict = None):
        """Add a single image to the index"""
        try:
            image = Image.open(image_path).convert('RGB')
            image_np = np.array(image)

            description = metadata.get('description', '') if metadata else ''

            # Encode
            if description:
                embedding = self.encode_multimodal(image_np, description)
            else:
                embedding = self.encode_image(image_np)

            # Train if needed
            if not self.is_trained:
                embedding_array = np.array([embedding], dtype=np.float32)
                self.index.train(embedding_array)
                self.is_trained = True

            embedding_array = np.array([embedding], dtype=np.float32)
            self.index.add(embedding_array)

            # Color
            color_lab = self._extract_color_lab(image_np)

            # Metadata
            item_metadata = metadata or {}
            item_metadata.update({
                'id': len(self.image_metadata),
                'path': image_path,
                'filename': os.path.basename(image_path),
                'color_lab': color_lab
            })
            self.image_metadata.append(item_metadata)

            return True
        except Exception as e:
            print(f"Error adding image {image_path}: {e}")
            return False
