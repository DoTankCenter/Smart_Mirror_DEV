from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import base64
import cv2
import numpy as np
from typing import List, Dict
import json

from segmentation.yolo_garment_segmenter import GarmentSegmenter
from search.enhanced_fashion_search import EnhancedFashionSearchEngine

app = FastAPI(title="Garment Bubble Visualization API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML models
garment_segmenter = None
fashion_search = None

@app.on_event("startup")
async def startup_event():
    global garment_segmenter, fashion_search
    print("Initializing ML models...")
    garment_segmenter = GarmentSegmenter(model_path='yolov8n-seg.pt', conf_threshold=0.5)
    fashion_search = EnhancedFashionSearchEngine()
    print("ML models loaded successfully!")

@app.get("/")
async def root():
    return {"message": "Garment Bubble Visualization API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "segmenter_ready": garment_segmenter is not None,
        "search_ready": fashion_search is not None
    }

@app.post("/process-frame")
async def process_frame(file: UploadFile = File(...)):
    """Process a single frame and return detected garments with similar items"""
    try:
        # Read image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Segment garments
        garments = garment_segmenter.segment_garments(image)

        # Find similar items for each garment
        results = []
        for garment in garments:
            similar_items = fashion_search.find_similar(garment['features'], top_k=5)
            results.append({
                "garment_id": garment['id'],
                "category": garment['category'],
                "bbox": garment['bbox'],
                "color": garment['color'],
                "similar_items": similar_items
            })

        return JSONResponse(content={"garments": results})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.websocket("/ws/camera-stream")
async def websocket_camera_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time camera stream processing"""
    await websocket.accept()
    print("WebSocket connection established")

    try:
        while True:
            # Receive frame data
            data = await websocket.receive_text()
            frame_data = json.loads(data)

            # Decode base64 image
            img_bytes = base64.b64decode(frame_data['frame'].split(',')[1])
            nparr = np.frombuffer(img_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Process frame
            garments = garment_segmenter.segment_garments(image)

            # Find similar items for each garment (only stable ones)
            results = []
            for garment in garments:
                if not garment.get('stable', True):
                    continue  # Skip unstable detections to prevent flicker

                similar_items = fashion_search.find_similar(
                    garment['features'],
                    garment_data={
                        'category': garment['category'],
                        'color_lab': garment['color_lab'],
                        'thumbnail': garment['thumbnail']
                    },
                    top_k=10  # Get more candidates for re-ranking
                )
                results.append({
                    "garment_id": garment['id'],
                    "person_id": garment['person_id'],
                    "category": garment['category'],
                    "fine_category": garment.get('fine_category', garment['category']),
                    "bbox": garment['bbox'],
                    "color": garment['color'],
                    "color_hex": garment['color_hex'],
                    "confidence": garment.get('confidence', 1.0),
                    "thumbnail": garment['thumbnail'],
                    "similar_items": similar_items[:5]  # Return top 5 after re-ranking
                })

            # Send results back
            await websocket.send_json({"garments": results})

    except WebSocketDisconnect:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"Error in WebSocket: {e}")
        await websocket.close()

@app.post("/index-library")
async def index_library(directory: str = "image_library"):
    """Index a directory of images for similarity search"""
    try:
        count = fashion_search.index_directory(directory)
        return {"message": f"Indexed {count} images successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
