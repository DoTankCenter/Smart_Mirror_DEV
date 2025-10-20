# Settings Guide - Dataset Configuration

This guide explains how to configure the dataset directory and other settings through the UI.

## Accessing Settings

1. Start the backend: `python backend/main.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Open the application in your browser
4. Click the **Settings** button in the top-right corner

## Settings Panel Features

### Dataset Configuration

#### Dataset Directory
Point to your existing dataset folder by entering the full path:

**Windows Examples:**
```
C:\Users\YourName\datasets\fashion_images
D:\data\clothing_dataset
image_library
```

**Linux/Mac Examples:**
```
/home/username/datasets/fashion_images
~/datasets/clothing_dataset
image_library
```

#### Metadata File
Specify the path to your metadata JSON file (optional but recommended for better search results):
```
metadata.json
C:\path\to\your\metadata.json
```

**Metadata Format:**
```json
{
  "image001.jpg": {
    "description": "red cotton t-shirt casual wear",
    "category": "top",
    "color": "red",
    "material": "cotton"
  }
}
```

#### Index Status
View the current status of your image library:
- **Index Status**: Shows if the library is indexed
- **Total Images**: Number of images in the index
- **Current Directory**: Currently configured dataset directory

#### Index Library Button
After setting your dataset directory, click **Index Library** to:
1. Scan all images in the specified folder
2. Generate FashionCLIP embeddings
3. Build the FAISS search index
4. Enable similarity search

### Model Configuration

#### Confidence Threshold (0.1 - 1.0)
Controls the minimum confidence for garment detection:
- **Lower (0.1-0.4)**: Detects more garments but may include false positives
- **Medium (0.5-0.7)**: Balanced detection (recommended)
- **Higher (0.8-1.0)**: Only high-confidence detections, stricter

#### Max Similar Items (1-20)
Maximum number of similar items to search from the dataset:
- More items = more accurate matching but slightly slower
- Recommended: 10-15 items

## Usage Workflow

### First Time Setup

1. **Open Settings** - Click the Settings button
2. **Set Dataset Directory** - Enter the path to your dataset folder
3. **Save Settings** - Click "Save Settings" button
4. **Index Library** - Click "Index Library" button and wait for completion
5. **Close Settings** - Click "Cancel" or the X button

### Changing Dataset Folder

1. Open Settings
2. Update the Dataset Directory field
3. Save Settings
4. Click "Index Library" to re-index the new folder
5. Wait for indexing to complete

### Using External Dataset

If you have an existing dataset in another location:

1. **Option A: Configure Path**
   - Open Settings
   - Enter full path to your dataset folder
   - Save and Index

2. **Option B: Create Symbolic Link** (Advanced)
   ```bash
   # Windows (run as admin)
   mklink /D image_library "C:\path\to\your\dataset"

   # Linux/Mac
   ln -s /path/to/your/dataset image_library
   ```

## Configuration Persistence

All settings are saved to `backend/config.json` and persist between application restarts.

**Default config.json:**
```json
{
  "dataset_directory": "image_library",
  "metadata_file": "metadata.json",
  "model_path": "yolov8n-seg.pt",
  "conf_threshold": 0.5,
  "max_similar_items": 10
}
```

## API Endpoints

You can also configure settings via API:

### Get Current Settings
```bash
curl http://localhost:8000/settings
```

### Update Settings
```bash
curl -X POST http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_directory": "C:\\path\\to\\dataset",
    "conf_threshold": 0.6
  }'
```

### Check Index Status
```bash
curl http://localhost:8000/index-status
```

### Index Library
```bash
curl -X POST http://localhost:8000/index-library \
  -H "Content-Type: application/json" \
  -d '{"directory": "C:\\path\\to\\dataset"}'
```

## Troubleshooting

### FAISS Installation Issues

If you encounter errors installing `faiss-gpu` due to Python version incompatibility:

- Try installing the CPU-only version:
  ```
  pip install faiss-cpu
  ```
- If FAISS is not compatible with your Python version, consider these alternatives:
  - **Annoy**: `pip install annoy`
  - **HNSWlib**: `pip install hnswlib`
  - **ScaNN**: `pip install scann` (requires TensorFlow)
- Alternatively, create a virtual environment with Python 3.8 or 3.9 for better FAISS compatibility.

> **Note:** If you switch to an alternative library, you will need to update the backend code to use the new library for similarity search and indexing.

### Directory Not Found Error
- Verify the path is correct and accessible
- Use absolute paths instead of relative paths
- On Windows, use double backslashes or forward slashes

### Indexing Takes Too Long
- Large datasets (10k+ images) may take several minutes
- Check console for progress messages
- Consider starting with a subset of images for testing

### Settings Not Saving
- Check file permissions in the backend directory
- Verify `config.json` is writable
- Check browser console for error messages

### Index Not Working
- Ensure the dataset directory contains valid image files
- Supported formats: .jpg, .jpeg, .png, .bmp, .webp
- Check backend logs for error messages

## Best Practices

1. **Start Small**: Test with 100-1000 images before indexing full dataset
2. **Use Metadata**: Provide descriptions and categories for better search results
3. **Organize Files**: Keep similar items in subdirectories
4. **Backup Config**: Save your `config.json` file
5. **Monitor Performance**: Larger datasets require more RAM and indexing time

## Performance Tips

- **RAM Usage**: ~600MB per 43k images
- **Indexing Time**: ~3-5 minutes for 43k images
- **Search Speed**: <10ms with proper indexing
- **Recommended Dataset Size**: 5k-100k images

## Support

For issues or questions:
1. Check backend console logs
2. Check browser console for frontend errors
3. Verify all paths are correct
4. Ensure sufficient disk space and RAM
