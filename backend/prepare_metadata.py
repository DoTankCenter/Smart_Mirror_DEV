"""
Helper script to create metadata.json for your 34k image library.

Expected format for each image:
{
  "filename.jpg": {
    "description": "red cotton t-shirt with short sleeves",
    "category": "top",
    "color": "red",
    "material": "cotton",
    "style": "casual"
  }
}

This script creates a template metadata file. You should populate it with your actual descriptions.
"""

import os
import json
from pathlib import Path

def create_metadata_template(image_directory: str, output_file: str = "metadata.json"):
    """
    Scan image directory and create a metadata template JSON file.
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    metadata = {}

    # Scan directory
    image_dir = Path(image_directory)
    if not image_dir.exists():
        print(f"Directory {image_directory} does not exist!")
        return

    image_files = []
    for ext in image_extensions:
        image_files.extend(image_dir.rglob(f'*{ext}'))

    print(f"Found {len(image_files)} images")

    # Create template entries
    for img_path in image_files:
        filename = img_path.name

        # Try to infer category from path
        category = "unknown"
        if any(x in str(img_path).lower() for x in ['top', 'shirt', 't-shirt', 'tshirt']):
            category = "top"
        elif any(x in str(img_path).lower() for x in ['bottom', 'pants', 'trousers', 'jeans']):
            category = "bottom"
        elif any(x in str(img_path).lower() for x in ['dress', 'gown']):
            category = "dress"
        elif any(x in str(img_path).lower() for x in ['shoe', 'shoes', 'sneaker', 'boot']):
            category = "shoes"
        elif any(x in str(img_path).lower() for x in ['jacket', 'coat', 'outerwear']):
            category = "outerwear"

        metadata[filename] = {
            "description": f"{category} garment",  # Placeholder - you should fill this in
            "category": category,
            "color": "",  # Optional
            "material": "",  # Optional
            "style": "",  # Optional
            "tags": []  # Optional
        }

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Created metadata template: {output_file}")
    print(f"Total entries: {len(metadata)}")
    print("\n⚠ IMPORTANT: Edit this file to add proper descriptions for better search results!")

def load_existing_descriptions(csv_file: str = None, txt_file: str = None):
    """
    If you have existing descriptions in CSV or TXT format, this function can help convert them.

    CSV format:
    filename,description,category
    img001.jpg,"red cotton t-shirt",top

    TXT format:
    img001.jpg: red cotton t-shirt (top)
    """
    # TODO: Implement CSV/TXT parsing if you have existing data
    pass

if __name__ == "__main__":
    # Usage
    IMAGE_DIR = "image_library"

    print("Creating metadata template...")
    create_metadata_template(IMAGE_DIR, "metadata.json")

    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("1. Edit metadata.json and fill in descriptions for each image")
    print("2. Good descriptions help FashionCLIP find better matches")
    print("   Example: 'red cotton t-shirt with short sleeves and crew neck'")
    print("3. After editing, run: python main.py")
    print("4. Then index: curl -X POST http://localhost:8000/index-library")
    print("="*60)
