"""
Download and prepare the Clothing Dataset Secondhand from Hugging Face.

Dataset: wargoninnovation/clothingdatasetsecondhand
- 43,100 images (30,200 train + 12,900 test)
- Product photos with removed backgrounds
- Rich metadata: brand, material, color, condition, season, etc.
- License: CC BY 4.0

This script:
1. Downloads the dataset from Hugging Face
2. Extracts images and metadata
3. Creates metadata.json for FashionCLIP indexing
4. Saves images to image_library/
"""

import os
import json
from pathlib import Path
from tqdm import tqdm
from PIL import Image
import io

# Install if needed: pip install datasets pillow tqdm
from datasets import load_dataset

def download_and_prepare_dataset(
    output_dir: str = "image_library",
    metadata_file: str = "metadata.json",
    split: str = "train",  # or "test" or "train+test"
    max_images: int = None  # Limit for testing, None = all
):
    """
    Download Hugging Face dataset and prepare for FashionCLIP indexing.

    Args:
        output_dir: Where to save images
        metadata_file: Where to save metadata JSON
        split: Dataset split ("train", "test", or "train+test")
        max_images: Limit number of images (None = download all)
    """
    print("="*60)
    print("Downloading Clothing Dataset Secondhand from Hugging Face")
    print("="*60)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load dataset
    print(f"\nLoading dataset (split: {split})...")
    if split == "train+test":
        dataset_train = load_dataset("wargoninnovation/clothingdatasetsecondhand", split="train")
        dataset_test = load_dataset("wargoninnovation/clothingdatasetsecondhand", split="test")
        # Combine
        from datasets import concatenate_datasets
        dataset = concatenate_datasets([dataset_train, dataset_test])
    else:
        dataset = load_dataset("wargoninnovation/clothingdatasetsecondhand", split=split)

    print(f"Ô£ô Loaded {len(dataset)} images")

    if max_images:
        dataset = dataset.select(range(min(max_images, len(dataset))))
        print(f"Limited to {len(dataset)} images for testing")

    # Process dataset
    metadata = {}
    processed_count = 0

    print("\nProcessing images...")
    for idx, item in enumerate(tqdm(dataset)):
        try:
            # Get image
            image = item.get('image')
            if image is None:
                continue

            # Generate filename
            filename = f"garment_{idx:06d}.jpg"
            filepath = os.path.join(output_dir, filename)

            # Save image
            if isinstance(image, Image.Image):
                image.save(filepath, 'JPEG', quality=90)
            else:
                # Handle if image is in different format
                img = Image.open(io.BytesIO(image))
                img.save(filepath, 'JPEG', quality=90)

            # Extract metadata attributes
            # Build rich description for FashionCLIP
            description_parts = []

            # Color
            color = item.get('colour', '') or item.get('color', '')
            if color:
                description_parts.append(color)

            # Material
            material = item.get('material', '')
            if material:
                description_parts.append(material)

            # Clothing type (infer from category or other fields)
            category = item.get('category', '') or item.get('type', '')

            # Brand (optional in description)
            brand = item.get('brand', '')

            # Condition
            condition = item.get('condition', '')

            # Season
            season = item.get('season', '')

            # Build natural language description
            if category:
                description_parts.insert(0, category)

            description = " ".join(description_parts).strip()

            if not description and category:
                description = category

            # Normalize category to our system
            category_normalized = normalize_category(category)

            # Store metadata
            metadata[filename] = {
                "description": description or "clothing item",
                "category": category_normalized,
                "original_category": category,
                "color": color,
                "material": material,
                "brand": brand,
                "condition": condition,
                "season": season,
                # Keep any other fields
                **{k: v for k, v in item.items() if k not in [
                    'image', 'colour', 'color', 'material', 'category',
                    'type', 'brand', 'condition', 'season'
                ]}
            }

            processed_count += 1

        except Exception as e:
            print(f"\nError processing image {idx}: {e}")
            continue

    # Save metadata
    print(f"\nÔ£ô Processed {processed_count} images")
    print(f"Saving metadata to {metadata_file}...")

    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Ô£ô Metadata saved")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Images saved: {processed_count}")
    print(f"Directory: {output_dir}")
    print(f"Metadata file: {metadata_file}")
    print(f"\nCategory distribution:")

    # Count categories
    category_counts = {}
    for meta in metadata.values():
        cat = meta.get('category', 'unknown')
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Start backend: python main.py")
    print("2. Index dataset: curl -X POST http://localhost:8000/index-library")
    print("3. Start frontend: cd frontend && npm run dev")
    print("4. Open http://localhost:3000")
    print("="*60)

    return processed_count

def normalize_category(category: str) -> str:
    """Normalize category names to our system (top/bottom/dress/shoes/outerwear)"""
    if not category:
        return "unknown"

    category_lower = category.lower()

    # Mapping rules
    if any(x in category_lower for x in ['dress', 'gown']):
        return 'dress'
    elif any(x in category_lower for x in ['trouser', 'pant', 'jean', 'short', 'skirt', 'legging']):
        return 'bottom'
    elif any(x in category_lower for x in ['shoe', 'boot', 'sneaker', 'sandal', 'heel']):
        return 'shoes'
    elif any(x in category_lower for x in ['jacket', 'coat', 'blazer', 'cardigan', 'hoodie', 'sweater', 'vest']):
        return 'outerwear'
    elif any(x in category_lower for x in ['shirt', 'blouse', 'top', 'tee', 't-shirt', 'tank', 'polo']):
        return 'top'
    else:
        # Default to top if unclear
        return 'top'

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Download Clothing Dataset Secondhand')
    parser.add_argument('--split', type=str, default='train',
                       choices=['train', 'test', 'train+test'],
                       help='Dataset split to download')
    parser.add_argument('--max-images', type=int, default=None,
                       help='Limit number of images (for testing)')
    parser.add_argument('--output-dir', type=str, default='image_library',
                       help='Output directory for images')

    args = parser.parse_args()

    # Download and prepare
    count = download_and_prepare_dataset(
        output_dir=args.output_dir,
        split=args.split,
        max_images=args.max_images
    )

    print(f"\nÔ£à Successfully downloaded and prepared {count} images!")
