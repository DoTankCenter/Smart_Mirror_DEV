# Debugging Guide - Garment Detection Issues

This guide helps you diagnose and fix issues when no garments are being detected.

## Quick Debug Steps

### 1. Open the Debug Panel

1. Start the application
2. Click the **Debug** button (top-right, teal color)
3. Enable **"Show Camera Preview"** checkbox
4. You should now see your camera feed in the top-left corner

### 2. Check Backend Status

The Debug Panel shows:
- **Backend Status**: Should be "Connected" (green)
- **Segmenter**: Should be "Ready"
- **Search**: Should be "Ready"
- **Index Status**: Shows if images are indexed

### 3. Check Camera Stream

- **Frames Sent**: Should be incrementing (10 per second)
- **Last Response**: Should update continuously
- **Garments Detected**: Shows detection count

## Common Issues & Solutions

### Issue: Backend Status shows "Disconnected"

**Problem**: Backend server is not running

**Solution**:
```bash
cd backend
python main.py
```

**Expected output**:
```
Initializing ML models...
ML models loaded successfully!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Issue: "Segmenter Not Ready"

**Problem**: YOLO model file missing

**Check**:
```bash
ls -lh yolov8n-seg.pt
```

**Solution** (if missing):
```bash
# Download from ultralytics
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8n-seg.pt')"
```

### Issue: "No Images Indexed"

**Problem**: Fashion search index is empty

**Solution**:
1. Click **Settings** button
2. Set **Dataset Directory** to your image folder
3. Click **Save Settings**
4. Click **Index Library**
5. Wait for indexing to complete

### Issue: Frames Sent but No Garments Detected

**Symptoms**:
- Frames counter incrementing
- Backend connected
- Camera preview visible
- But "Garments Detected" stays at 0

**Possible Causes & Solutions**:

#### A. Poor Lighting
- Ensure well-lit environment
- Avoid backlighting
- Use natural or bright white light

#### B. Camera Distance
- Stand 2-3 meters from camera
- Too close: may only detect parts
- Too far: too small to detect

#### C. Clothing Visibility
- Wear contrasting colors
- Avoid patterns that blend with background
- Ensure full garment is visible

#### D. Confidence Threshold Too High
1. Open **Settings**
2. Lower **Confidence Threshold** to 0.3-0.4
3. Save and try again

#### E. Camera Not Showing You
- Check camera preview
- Ensure you're in frame
- Verify camera is not covered

### Issue: WebSocket Connection Fails

**Symptoms**:
- Status shows "Disconnected"
- No frames being sent
- Console error: "WebSocket error"

**Solutions**:

1. **Check Backend Port**:
```bash
# Should show Python listening on port 8000
netstat -ano | findstr :8000
```

2. **Firewall Blocking**:
- Allow Python through Windows Firewall
- Or run as administrator temporarily

3. **Wrong WebSocket URL**:
- Should be: `ws://localhost:8000/ws/camera-stream`
- Check App.jsx line 28

### Issue: Camera Permission Denied

**Symptoms**:
- Browser alert: "Camera access denied"
- No camera preview

**Solutions**:

1. **Chrome**:
   - Click lock icon in address bar
   - Set Camera to "Allow"
   - Reload page

2. **Edge**:
   - Settings → Privacy → Camera
   - Allow for localhost

3. **Firefox**:
   - Click shield icon
   - Permissions → Camera → Allow

## Debug Panel Features

### Camera Preview
- **Show Camera Preview**: Displays live camera feed in top-left
- Useful for verifying what the camera sees
- Shows same view being sent to backend

### Frame Statistics
- **Frames Sent**: Total frames sent to backend
- Should increment by ~10 per second
- If stuck at 0: WebSocket not connected

### Detection Details
When garments are detected, you'll see:
- **Garment ID**: Unique identifier
- **Category**: Type (top, bottom, dress, etc.)
- **Color**: Detected color in hex
- **Confidence**: Detection confidence (0-100%)
- **Thumbnail**: Small preview of detected garment

### Backend Health
- **Connected/Disconnected**: WebSocket status
- **Segmenter Ready**: YOLO model loaded
- **Search Ready**: FashionCLIP model loaded

### Index Information
- **Indexed**: Yes/No
- **Total Items**: Number of images in search index
- **Directory**: Current dataset path

## Advanced Debugging

### Check Backend Logs

Open a new terminal and run:
```bash
cd backend
python main.py
```

Watch for errors like:
- `Error loading model`
- `CUDA out of memory`
- `File not found`

### Check Browser Console

Press F12 in browser and check Console tab:
- Look for WebSocket errors
- Check for frame sending logs
- Verify garment data structure

### Test Backend Directly

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","segmenter_ready":true,"search_ready":true}
```

### Test with Sample Image

```bash
curl -X POST http://localhost:8000/process-frame \
  -F "file=@test_image.jpg"
```

## Performance Tips

### GPU Detection
```python
import torch
print(torch.cuda.is_available())  # Should be True if GPU available
```

### Memory Issues
If detection is slow or crashes:
- Close other applications
- Reduce camera resolution in CameraStream.js:
  ```javascript
  width: { ideal: 640 },  // Lower from 1280
  height: { ideal: 480 }, // Lower from 720
  ```

### CPU Mode
If no GPU available:
- Detection will be slower (5-10 FPS)
- Still works, just less responsive
- Consider increasing frame send interval to 200ms

## Testing Checklist

- [ ] Backend running (`python main.py`)
- [ ] Backend health returns OK
- [ ] Frontend running (`npm run dev`)
- [ ] Debug panel shows "Connected"
- [ ] Camera preview visible
- [ ] Frames counter incrementing
- [ ] Good lighting setup
- [ ] 2-3 meters from camera
- [ ] Wearing visible clothing
- [ ] Confidence threshold appropriate (0.4-0.6)
- [ ] Dataset indexed (if using search)

## Still Not Working?

1. **Restart Everything**:
   - Stop backend (Ctrl+C)
   - Stop frontend (Ctrl+C)
   - Clear browser cache
   - Restart backend
   - Restart frontend

2. **Check System Requirements**:
   - Python 3.9+
   - Node.js 18+
   - Webcam connected
   - 8GB+ RAM
   - GPU recommended but not required

3. **Verify Installation**:
```bash
# Backend dependencies
cd backend
pip list | grep -E "torch|ultralytics|opencv"

# Frontend dependencies
cd frontend
npm list | grep -E "react|three|matter"
```

## Example Working Configuration

**Backend Output**:
```
Initializing ML models...
Loading FashionCLIP model: patrickjohncyh/fashion-clip
FashionCLIP loaded on cuda
ML models loaded successfully!
WebSocket connection established
```

**Debug Panel**:
```
Backend Status: Connected
Segmenter: Ready
Search: Ready
Frames Sent: 142
Last Response: 14:23:45
Garments Detected: 2
```

## Contact & Support

If you're still experiencing issues:
1. Check backend terminal for Python errors
2. Check browser console (F12) for JavaScript errors
3. Take screenshots of Debug Panel
4. Note what you've already tried

## Quick Reference Commands

```bash
# Start backend
cd backend && python main.py

# Start frontend
cd frontend && npm run dev

# Check backend health
curl http://localhost:8000/health

# Check index status
curl http://localhost:8000/index-status

# View backend settings
curl http://localhost:8000/settings
```
