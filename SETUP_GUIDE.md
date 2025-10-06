# Quick Setup Guide

Follow these steps to get your Garment Bubble Visualization app running.

## Step 1: Backend Setup

### Windows

```powershell
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create image library directory
mkdir image_library
```

### macOS/Linux

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create image library directory
mkdir image_library
```

## Step 2: Add Fashion Images

1. Download or collect fashion images (clothing items, garments)
2. Place them in the `backend/image_library/` directory
3. Supported formats: JPG, PNG, WEBP, BMP

**Tip**: Organize images in subdirectories by category for easier management:
```
image_library/
Ôö£ÔöÇÔöÇ tops/
Ôö£ÔöÇÔöÇ bottoms/
Ôö£ÔöÇÔöÇ shoes/
ÔööÔöÇÔöÇ accessories/
```

## Step 3: Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install
```

## Step 4: Start the Application

### Terminal 1 - Backend
```bash
cd backend
# Activate venv if not already activated
python main.py
```

Wait for the message: "ML models loaded successfully!"

### Terminal 2 - Index Your Library (First Time Only)
```bash
# Wait for backend to finish loading, then:
curl -X POST "http://localhost:8000/index-library"
```

You should see: `{"message":"Indexed X images successfully"}`

### Terminal 3 - Frontend
```bash
cd frontend
npm run dev
```

## Step 5: Open in Browser

1. Navigate to `http://localhost:3000`
2. Allow camera access when prompted
3. Stand in front of the camera
4. Watch the magic happen! Ô£¿

## Verification Checklist

- [ ] Python 3.9+ installed
- [ ] Node.js 18+ installed
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Camera permissions granted
- [ ] At least 10 images in image_library/
- [ ] Images indexed successfully

## Quick Test

After setup, test the API:

```bash
# Check backend health
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "segmenter_ready": true,
  "search_ready": true
}
```

## Common Setup Issues

### Issue: "No module named 'cv2'"
**Solution**: Reinstall OpenCV
```bash
pip uninstall opencv-python
pip install opencv-python==4.9.0.80
```

### Issue: "torch not found" or CUDA errors
**Solution**: Install CPU version explicitly
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Issue: "Port 8000 already in use"
**Solution**: Kill the process using port 8000
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### Issue: Frontend won't connect to backend
**Solution**: Check CORS and WebSocket settings
- Ensure backend is running first
- Check browser console for errors
- Verify WebSocket URL in `CameraStream.js` matches your backend

### Issue: Camera not working
**Solution**:
- Use Chrome or Edge (best WebRTC support)
- Ensure HTTPS or localhost
- Check browser camera permissions in settings
- Try different browser

## Next Steps

Once running:
1. Adjust physics controls (bottom-right gear icon)
2. Try different lighting conditions
3. Test with multiple people
4. Experiment with different garment types

## Getting More Images

Free fashion image datasets:
- **DeepFashion**: Research dataset with 800K+ images
- **Fashion-MNIST**: Simple fashion item images
- **ASOS/Zalando**: Scrape product images (check terms of service)
- **Unsplash/Pexels**: Free stock photos of clothing

## Performance Optimization

For better performance on slower machines:

1. **Reduce camera resolution** in `frontend/src/utils/CameraStream.js`:
```javascript
video: {
  width: { ideal: 640 },  // Instead of 1280
  height: { ideal: 480 }   // Instead of 720
}
```

2. **Lower frame rate** in `CameraStream.js`:
```javascript
setTimeout(sendFrame, 200)  // 5 FPS instead of 10 FPS
```

3. **Reduce similar items** in the control panel (set to 3 instead of 5)

## Need Help?

Check the main README.md for detailed documentation and troubleshooting.
