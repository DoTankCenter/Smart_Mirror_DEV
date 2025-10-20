from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import base64
import cv2
import numpy as np
from typing import List, Dict, Optional
import json
import os

from segmentation.yolo_garment_segmenter import GarmentSegmenter
from search.enhanced_fashion_search import EnhancedFashionSearchEngine
from config import ConfigManager

app = FastAPI(title="Garment Bubble Visualization API")

# CORS middleware - allow all localhost ports for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class SettingsUpdate(BaseModel):
    dataset_directory: Optional[str] = None
    metadata_file: Optional[str] = None
    conf_threshold: Optional[float] = None
    max_similar_items: Optional[int] = None

class IndexRequest(BaseModel):
    directory: Optional[str] = None

# Initialize configuration and ML models
config_manager = ConfigManager()
garment_segmenter = None
fashion_search = None

@app.on_event("startup")
async def startup_event():
    global garment_segmenter, fashion_search
    print("Initializing ML models...")
    conf_threshold = config_manager.get('conf_threshold', 0.5)
    model_path = config_manager.get('model_path', 'yolov8n-seg.pt')
    garment_segmenter = GarmentSegmenter(model_path=model_path, conf_threshold=conf_threshold)
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

            print(f"DEBUG: WebSocket received {len(garments)} garments from segmenter")

            # Find similar items for each garment (only stable ones)
            results = []
            for garment in garments:
                if not garment.get('stable', True):
                    # Get stable_frames from garment_cache via garment_key
                    garment_key = f"{garment['person_id']}_{garment['category']}"
                    stable_frames = garment_segmenter.garment_cache.get(garment_key, {}).get('stable_frames', 0)
                    print(f"DEBUG: Skipping unstable garment {garment['category']} ({stable_frames}/3 frames)")
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
                garment_result = {
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
                }
                results.append(garment_result)
                print(f"DEBUG: Sending stable garment {garment['category']} with {len(similar_items[:5])} similar items")

            # Send results back
            print(f"DEBUG: Sending {len(results)} stable garments to frontend")
            await websocket.send_json({"garments": results})

    except WebSocketDisconnect:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"Error in WebSocket: {e}")
        await websocket.close()

@app.post("/index-library")
async def index_library(request: IndexRequest = Body(default=IndexRequest())):
    """Index a directory of images for similarity search"""
    try:
        # Use provided directory or get from config
        directory = request.directory or config_manager.get('dataset_directory', 'image_library')
        metadata_file = config_manager.get('metadata_file', 'metadata.json')

        # Check if directory exists
        if not os.path.exists(directory):
            return JSONResponse(
                status_code=400,
                content={"error": f"Directory not found: {directory}"}
            )

        # Index with metadata if available
        if os.path.exists(metadata_file):
            count = fashion_search.index_directory(directory, metadata_file)
        else:
            count = fashion_search.index_directory(directory)

        return {
            "message": f"Indexed {count} images successfully",
            "directory": directory,
            "count": count
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/settings")
async def get_settings():
    """Get current application settings"""
    return config_manager.get_all()

@app.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update application settings"""
    try:
        updates = {}

        # Validate and update dataset directory
        if settings.dataset_directory is not None:
            if config_manager.validate_directory(settings.dataset_directory):
                updates['dataset_directory'] = settings.dataset_directory
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Invalid directory: {settings.dataset_directory}"}
                )

        # Update other settings
        if settings.metadata_file is not None:
            updates['metadata_file'] = settings.metadata_file

        if settings.conf_threshold is not None:
            if 0 < settings.conf_threshold <= 1:
                updates['conf_threshold'] = settings.conf_threshold
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": "conf_threshold must be between 0 and 1"}
                )

        if settings.max_similar_items is not None:
            if settings.max_similar_items > 0:
                updates['max_similar_items'] = settings.max_similar_items
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": "max_similar_items must be greater than 0"}
                )

        # Apply updates
        if updates:
            success = config_manager.update(updates)
            if success:
                return {
                    "message": "Settings updated successfully",
                    "settings": config_manager.get_all()
                }
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to save settings"}
                )
        else:
            return {"message": "No changes to apply", "settings": config_manager.get_all()}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/index-status")
async def index_status():
    """Get current index status"""
    return {
        "indexed": fashion_search.is_trained if fashion_search else False,
        "total_items": fashion_search.index.ntotal if fashion_search and fashion_search.is_trained else 0,
        "current_directory": config_manager.get('dataset_directory', 'image_library')
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
