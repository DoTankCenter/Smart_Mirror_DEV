import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import faiss
import numpy as np
import os
from typing import List, Dict
import pickle

class FashionSearchEngine:
    """Semantic search for fashion items using FashionCLIP"""

    def __init__(self, model_name: str = "patrickjohncyh/fashion-clip"):
        print(f"Loading FashionCLIP model: {model_name}")

        # Load FashionCLIP model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

        # Initialize FAISS index
        self.dimension = 512  # CLIP embedding dimension
        self.index = faiss.IndexFlatL2(self.dimension)

        # Store metadata for indexed images
        self.image_metadata = []

        print(f"FashionCLIP loaded on {self.device}")

    def encode_image(self, image: np.ndarray) -> np.ndarray:
        """Encode an image to a feature vector using FashionCLIP"""
        # Convert numpy array to PIL Image
        if isinstance(image, np.ndarray):
            if image.shape[2] == 4:  # RGBA
                image = image[:, :, :3]  # Drop alpha channel
            pil_image = Image.fromarray(image)
        else:
            pil_image = image

        # Process image
        inputs = self.processor(images=pil_image, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get embeddings
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0]

    def encode_features(self, features: List[float]) -> np.ndarray:
        """
        Convert basic feature vector to FashionCLIP-compatible embedding.
        This is a simplified approach using the color histogram features.
        For production, you'd want to pass the actual image through FashionCLIP.
        """
        # For now, we'll just pad/project the features to the CLIP dimension
        # In a real implementation, this should use the actual garment image
        features_array = np.array(features, dtype=np.float32)

        # Simple projection: repeat and normalize to match CLIP dimension
        if len(features_array) < self.dimension:
            # Repeat features to match dimension
            repetitions = self.dimension // len(features_array) + 1
            projected = np.tile(features_array, repetitions)[:self.dimension]
        else:
            projected = features_array[:self.dimension]

        # Normalize
        projected = projected / (np.linalg.norm(projected) + 1e-8)

        return projected

    def find_similar(self, features: List[float], top_k: int = 5) -> List[Dict]:
        """Find similar items from the indexed library"""
        if self.index.ntotal == 0:
            return []  # No items indexed yet

        # Convert features to embedding
        query_embedding = self.encode_features(features)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        # Search
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.image_metadata):
                item = self.image_metadata[idx].copy()
                item['similarity'] = float(1 / (1 + dist))  # Convert distance to similarity
                results.append(item)

        return results

    def index_directory(self, directory: str) -> int:
        """Index all images in a directory for similarity search"""
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist. Creating it...")
            os.makedirs(directory, exist_ok=True)
            return 0

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
                # Load image
                image = Image.open(image_path).convert('RGB')

                # Encode
                embedding = self.encode_image(np.array(image))
                embeddings.append(embedding)

                # Store metadata
                metadata.append({
                    'id': idx,
                    'path': image_path,
                    'filename': os.path.basename(image_path)
                })

                if (idx + 1) % 100 == 0:
                    print(f"Indexed {idx + 1}/{len(image_files)} images")

            except Exception as e:
                print(f"Error indexing {image_path}: {e}")

        # Add to FAISS index
        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            self.index.add(embeddings_array)
            self.image_metadata.extend(metadata)

            print(f"Successfully indexed {len(embeddings)} images")

        return len(embeddings)

    def save_index(self, path: str = "fashion_index.pkl"):
        """Save the index and metadata to disk"""
        faiss.write_index(self.index, path + ".faiss")

        with open(path, 'wb') as f:
            pickle.dump(self.image_metadata, f)

        print(f"Index saved to {path}")

    def load_index(self, path: str = "fashion_index.pkl"):
        """Load the index and metadata from disk"""
        if not os.path.exists(path + ".faiss"):
            print(f"Index file {path}.faiss not found")
            return False

        self.index = faiss.read_index(path + ".faiss")

        with open(path, 'rb') as f:
            self.image_metadata = pickle.load(f)

        print(f"Index loaded: {self.index.ntotal} items")
        return True

    def add_image(self, image_path: str, metadata: Dict = None):
        """Add a single image to the index"""
        try:
            image = Image.open(image_path).convert('RGB')
            embedding = self.encode_image(np.array(image))

            embedding_array = np.array([embedding], dtype=np.float32)
            self.index.add(embedding_array)

            item_metadata = metadata or {}
            item_metadata.update({
                'id': len(self.image_metadata),
                'path': image_path,
                'filename': os.path.basename(image_path)
            })
            self.image_metadata.append(item_metadata)

            return True
        except Exception as e:
            print(f"Error adding image {image_path}: {e}")
            return False
