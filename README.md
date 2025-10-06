# Garment Bubble Visualization

An interactive application that uses computer vision to detect clothing from a camera feed and visualizes them as physics-based bubbles with semantic search for similar fashion items.

## Features

- **Real-time Garment Segmentation**: Uses MediaPipe to segment clothing items (tops, bottoms, shoes) from camera feed
- **Semantic Fashion Search**: Employs FashionCLIP to find similar garments from your image library
- **Physics-Based Visualization**: Beautiful bubble animations using Matter.js with realistic collision and bouncing
- **Multi-Person Support**: Tracks multiple people simultaneously with separate bubble clusters
- **Interactive Controls**: Adjust physics parameters in real-time (gravity, bounciness, friction, bubble sizes)
- **3D Rendering**: Smooth WebGL rendering with Three.js for visual effects

## Architecture

### Backend (Python + FastAPI)
- **Garment Segmentation**: MediaPipe Pose + Selfie Segmentation for clothing detection
- **Feature Extraction**: Color histograms and shape features from segmented regions
- **Semantic Search**: FashionCLIP embeddings with FAISS vector database
- **WebSocket Streaming**: Real-time camera frame processing

### Frontend (React + Three.js + Matter.js)
- **Camera Capture**: WebRTC getUserMedia for camera access
- **Physics Engine**: Matter.js for realistic bubble physics and collisions
- **Rendering**: Three.js/WebGL for smooth 60 FPS visualization
- **UI Controls**: Real-time physics parameter adjustment

## Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- Webcam access

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create an image library directory:
```bash
mkdir image_library
```

6. Add fashion images to `image_library/` (organize in subdirectories if desired)

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Running the Application

### 1. Start the Backend

```bash
cd backend
python main.py
```

The backend will start on `http://localhost:8000`

### 2. Index Your Image Library (First Time Only)

Open a new terminal and run:

```bash
curl -X POST "http://localhost:8000/index-library" -H "Content-Type: application/json" -d '{"directory": "image_library"}'
```

Or visit: `http://localhost:8000/docs` and use the interactive API docs

### 3. Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:3000`

### 4. Open in Browser

Navigate to `http://localhost:3000` and allow camera access when prompted.

## Usage

### Camera Positioning
- Stand in front of the camera with good lighting
- Ensure full body is visible for best garment detection
- Multiple people can be in frame simultaneously

### Controls
Click the **⚙** button in the bottom-right to open the control panel:

- **Gravity**: Adjust downward force on bubbles (0 = floating, 2 = heavy)
- **Bounciness**: Control bubble elasticity (0 = no bounce, 1 = super bouncy)
- **Friction**: Adjust sliding resistance (0 = slippery, 0.1 = sticky)
- **Similar Items Count**: Number of similar items to display per garment (1-10)
- **Main Bubble Size**: Size of detected garment bubbles (40-150px)
- **Satellite Bubble Size**: Size of similar item bubbles (15-60px)

### Visualization
- **Large bubbles**: Detected garments from the camera (colored based on garment)
- **Small bubbles**: Similar items from your library (orbiting around main bubbles)
- **Labels**: Garment categories (TOP, BOTTOM, SHOES)

## API Endpoints

### REST Endpoints
- `GET /` - API status
- `GET /health` - Health check
- `POST /process-frame` - Process a single image frame
- `POST /index-library` - Index fashion image library

### WebSocket
- `ws://localhost:8000/ws/camera-stream` - Real-time camera stream processing

## Project Structure

```
Smart_Mirror_test1/
├── backend/
│   ├── main.py                    # FastAPI server
│   ├── requirements.txt           # Python dependencies
│   ├── segmentation/
│   │   └── garment_segmenter.py  # MediaPipe segmentation
│   └── search/
│       └── fashion_search.py      # FashionCLIP search engine
├── frontend/
│   ├── package.json               # Node dependencies
│   ├── vite.config.js             # Vite configuration
│   ├── index.html                 # Entry HTML
│   └── src/
│       ├── main.jsx               # React entry point
│       ├── App.jsx                # Main app component
│       ├── components/
│       │   ├── BubbleCanvas.jsx   # Three.js renderer
│       │   └── ControlPanel.jsx   # Physics controls UI
│       ├── physics/
│       │   └── BubblePhysics.js   # Matter.js physics engine
│       └── utils/
│           └── CameraStream.js    # WebSocket camera handler
└── README.md
```

## Technology Stack

### Computer Vision & ML
- **MediaPipe**: Body pose detection and selfie segmentation
- **FashionCLIP**: Fashion-specific CLIP model for semantic search
- **FAISS**: Vector similarity search
- **PyTorch**: Deep learning framework

### Backend
- **FastAPI**: Modern Python web framework
- **OpenCV**: Image processing
- **NumPy**: Numerical computing

### Frontend
- **React**: UI framework
- **Three.js**: 3D/WebGL rendering
- **Matter.js**: 2D physics engine
- **Vite**: Build tool and dev server

## Performance Notes

- Camera frames are processed at ~10 FPS to balance accuracy and performance
- Physics simulation runs at 60 FPS for smooth animations
- FashionCLIP inference runs on GPU if available (falls back to CPU)
- FAISS provides efficient similarity search even with large image libraries

## Customization

### Adjusting Segmentation
Edit `backend/segmentation/garment_segmenter.py`:
- Modify landmark-based region detection
- Adjust contour area thresholds
- Change feature extraction methods

### Modifying Physics
Edit `frontend/src/physics/BubblePhysics.js`:
- Adjust collision groups for different behaviors
- Modify spring constraints between bubbles
- Change boundary configurations

### Styling Bubbles
Edit `frontend/src/components/BubbleCanvas.jsx`:
- Customize gradient colors and effects
- Modify glow and transparency
- Add custom textures or patterns

## Troubleshooting

### Camera Not Detected
- Ensure browser has camera permissions
- Try using HTTPS (required by some browsers)
- Check if another application is using the camera

### Backend Connection Failed
- Verify backend is running on port 8000
- Check firewall settings
- Ensure WebSocket connections are allowed

### Poor Segmentation Quality
- Improve lighting conditions
- Ensure clear background separation
- Adjust MediaPipe confidence thresholds

### Performance Issues
- Reduce camera resolution in `CameraStream.js`
- Lower frame processing rate
- Decrease number of similar items to display

## Future Enhancements

- [ ] Add garment texture visualization on bubbles
- [ ] Implement outfit compatibility scoring
- [ ] Support custom trained segmentation models
- [ ] Add recording/screenshot functionality
- [ ] Create mobile app version
- [ ] Add AR mode with virtual try-on
- [ ] Support video file input (not just live camera)
- [ ] Add voice commands for controls

## License

MIT License - feel free to use this project for any purpose.

## Credits

- MediaPipe by Google
- FashionCLIP by Patrick John et al.
- Matter.js physics engine
- Three.js 3D library

## Support

For issues, questions, or suggestions, please open an issue on the project repository.
