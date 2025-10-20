# Alternative Garment Segmentation Models

The default `yolov8n-seg.pt` model detects general objects (COCO dataset), not clothing. Here are better alternatives:

---

## Option 1: Cloth-Segmentation (RECOMMENDED)

**Best for:** Quick setup, accurate clothing detection

### Installation
```bash
cd backend
pip install cloth-segmentation
```

### Usage
Update `backend/main.py` line 33:
```python
# Change from:
garment_segmenter = GarmentSegmenter(model_path='yolov8n-seg.pt', conf_threshold=0.5)

# To:
from segmentation.cloth_segmenter import ClothSegmenter
garment_segmenter = ClothSegmenter()
```

### Pros
- Works immediately, no training needed
- Specifically designed for clothing
- Fast inference (~30ms per frame)
- Accurate segmentation masks

### Cons
- Only segments "clothing" as one class, doesn't distinguish top/bottom/shoes
- Requires separate logic to split into garment types (already implemented)

---

## Option 2: Fashion-Specific YOLO Model

**Best for:** Multi-class garment detection (top, bottom, dress, shoes)

### Download Pre-trained Model

**Option A: From Roboflow Universe**
1. Visit: https://universe.roboflow.com/fashion-datasets
2. Search for "clothing segmentation" or "fashion segmentation"
3. Download YOLOv8 segmentation model
4. Place in backend directory

**Option B: Train Your Own**
```bash
pip install ultralytics
python train_fashion_yolo.py  # See training script below
```

### Usage
```python
# In backend/main.py line 33:
garment_segmenter = GarmentSegmenter(
    model_path='path/to/fashion-yolo.pt',
    conf_threshold=0.4
)
```

### Pros
- Detects specific garment types (top, bottom, dress, shoes, etc.)
- Instance segmentation (multiple garments per person)
- Can detect accessories

### Cons
- Requires finding/training a model
- Larger model size
- May need fine-tuning for your use case

---

## Option 3: Detectron2 with DeepFashion2

**Best for:** Highest accuracy, research applications

### Installation
```bash
pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu118/torch2.0/index.html
# Adjust CUDA version as needed
```

### Download Model
```bash
wget https://github.com/switchablenorms/DeepFashion2/releases/download/v1.0/deepfashion2_detectron2.pth
```

### Pros
- State-of-the-art accuracy
- Trained on large fashion dataset (DeepFashion2)
- Detects 13 garment categories
- Includes keypoints and attributes

### Cons
- More complex setup
- Heavier model (slower inference)
- Requires more dependencies

---

## Option 4: Segment Anything Model (SAM)

**Best for:** Universal segmentation, maximum flexibility

### Installation
```bash
pip install segment-anything
# Download model
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
```

### Pros
- Can segment ANY object
- State-of-the-art segmentation quality
- Works with prompts or automatic mode

### Cons
- Very slow (~1-2 seconds per frame on GPU)
- Requires prompts or bounding boxes
- Not specifically trained for fashion
- Large model (2.4GB+)

---

## Comparison Table

| Model | Accuracy | Speed | Ease of Use | Garment Types | Size |
|-------|----------|-------|-------------|---------------|------|
| **Cloth-Segmentation** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Binary (yes/no) | 176MB |
| **Fashion YOLO** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 5-13 classes | 6-50MB |
| **Detectron2** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | 13 classes | 400MB+ |
| **SAM** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | Universal | 2.4GB |

---

## Quick Start: Use Cloth-Segmentation

**1. Install:**
```bash
cd backend
pip install cloth-segmentation
```

**2. Modify `backend/main.py` (around line 33):**
```python
# Replace this line:
from segmentation.yolo_garment_segmenter import GarmentSegmenter
garment_segmenter = GarmentSegmenter(model_path='yolov8n-seg.pt', conf_threshold=0.5)

# With this:
from segmentation.cloth_segmenter import ClothSegmenter
garment_segmenter = ClothSegmenter()
```

**3. Restart backend:**
```bash
python main.py
```

**4. Test:**
Stand in front of camera - should now detect clothing much better!

---

## Training Custom Fashion YOLO (Advanced)

If you want to train your own YOLOv8 model on fashion data:

```python
# train_fashion_yolo.py
from ultralytics import YOLO

# Download DeepFashion2 or similar dataset
# Format as YOLO segmentation dataset

model = YOLO('yolov8n-seg.pt')  # Start from pretrained

results = model.train(
    data='fashion_dataset.yaml',  # Your dataset config
    epochs=100,
    imgsz=640,
    batch=16,
    device=0  # GPU
)

# Save best model
model.save('fashion-yolov8-seg.pt')
```

---

## Recommended Path for You

Based on your setup (1537 indexed images, CUDA available):

1. **Start with Cloth-Segmentation** (5 minutes setup)
   - Quick to test
   - Will work immediately
   - Good accuracy for clothing

2. **If you need better garment classification:**
   - Search Roboflow Universe for fashion YOLO model
   - Or train your own on your 1537 images

3. **For production with highest quality:**
   - Use Detectron2 with DeepFashion2
   - More setup but best results

---

## Installation Commands

### Cloth-Segmentation (Recommended First)
```bash
cd backend
pip install cloth-segmentation scikit-image
```

### Fashion YOLO (If training)
```bash
pip install ultralytics roboflow
```

### Detectron2 (Advanced)
```bash
pip install 'git+https://github.com/facebookresearch/detectron2.git'
```

### SAM (Research)
```bash
pip install segment-anything
```

---

## Support & Resources

- **Cloth-Segmentation:** https://github.com/levindabhi/cloth-segmentation
- **DeepFashion2:** https://github.com/switchablenorms/DeepFashion2
- **Roboflow Fashion Models:** https://universe.roboflow.com/search?q=fashion
- **YOLOv8 Training:** https://docs.ultralytics.com/modes/train/
- **SAM:** https://github.com/facebookresearch/segment-anything

---

## Current Status

Your system is currently using:
- ❌ `yolov8n-seg.pt` (COCO model - detects general objects, not clothing)
- ✅ Workaround: Converting "person" detections to synthetic top/bottom

**This works but is not ideal.** Switching to Cloth-Segmentation or a fashion-specific model will give much better results.
