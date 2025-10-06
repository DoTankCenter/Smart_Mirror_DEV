# Architecture - Garment Bubble Visualization

## System Overview

```
ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ          ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ          ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ
Ôöé   Camera        Ôöé   WebRTC Ôöé   Backend        Ôöé  WebSocketÔöé   Frontend      Ôöé
Ôöé   (getUserMedia)ÔöéÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔûÂÔöé   FastAPI        ÔöéÔùÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöé   React + Three.jsÔöé
ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ          ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ          ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ
                                      Ôöé
                                      Ôû╝
                            ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ
                            Ôöé  ML Pipeline         Ôöé
                            Ôöé  - YOLOv8-seg        Ôöé
                            Ôöé  - FashionCLIP       Ôöé
                            Ôöé  - FAISS Search      Ôöé
                            ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ
```

## Refined Architecture (Based on Research)

### Backend Components

#### 1. Garment Segmentation ([yolo_garment_segmenter.py](backend/segmentation/yolo_garment_segmenter.py))

**Model**: YOLOv8n-seg (nano) for real-time performance

**Process**:
1. Input: Camera frame (640├ù480 or 768├ù432)
2. YOLOv8 detects garment instances with masks
3. Spatial clustering to group garments by person
4. Per-garment processing:
   - Extract clean mask (RLE encoded if needed)
   - LAB color extraction with K-means (k=3)
   - Bounding box computation
   - Feature vector generation (color hist + texture)

**Key Features**:
- Ô£à **Instance segmentation** - Each garment is a separate object
- Ô£à **Multi-person support** - Spatial clustering groups garments by person
- Ô£à **Category detection** - Automatic classification (top/bottom/dress/shoes/outerwear)
- Ô£à **Temporal stability** - EMA filtering for smooth colors
- Ô£à **Spawn/fade rules** - Garments must be stable for 3 frames before appearing

**Output per garment**:
```json
{
  "id": 42,
  "person_id": 0,
  "category": "top",
  "fine_category": "short_sleeve_top",
  "bbox": [x, y, w, h],
  "color": [r, g, b],
  "color_lab": [L, a, b],
  "color_hex": "#FF5733",
  "confidence": 0.92,
  "stable": true,
  "features": [96-dim vector],
  "thumbnail": "data:image/jpeg;base64,..."
}
```

**Performance**:
- 15-30 FPS on RTX 3060/3070
- ~50ms per frame @ 640├ù480

---

#### 2. Enhanced Semantic Search ([enhanced_fashion_search.py](backend/search/enhanced_fashion_search.py))

**Model**: FashionCLIP (fine-tuned CLIP for fashion)

**Index**: FAISS IVF with HNSW (optimized for 34k images)

**Process**:

**A. Indexing (one-time)**
```python
# For each image in library:
1. Load image
2. Load metadata (description, category, etc.)
3. Encode with multimodal fusion:
   - Image embedding (FashionCLIP vision encoder)
   - Text embedding (FashionCLIP text encoder)
   - Weighted fusion: 0.7 * image + 0.3 * text
4. Extract LAB color for re-ranking
5. Store in FAISS + metadata array
```

**B. Search (real-time)**
```python
# For each detected garment:
1. Convert feature vector to embedding (normalized)
2. FAISS search ÔåÆ top 30 candidates
3. Re-rank by:
   - Category match (1.2x boost if same category)
   - Color similarity (LAB Delta E < 30 ÔåÆ up to 1.3x boost)
4. Return top 5
```

**Re-ranking Formula**:
```
final_score = base_similarity
              ├ù (1.2 if category_match else 1.0)
              ├ù (1 + 0.3 ├ù color_similarity)
```

**Performance**:
- <10ms per query with HNSW
- ~500ms for full 34k library indexing (one-time)

---

### Frontend Components

#### 3. Enhanced Bubble Physics ([EnhancedBubblePhysics.js](frontend/src/physics/EnhancedBubblePhysics.js))

**Engine**: Matter.js with fixed timestep (60 FPS)

**Key Features**:
- Ô£à **Spawn stability** - Garments must appear for 3 frames before bubble spawns
- Ô£à **Fade in/out** - 20 frames spawn, 15 frames fade
- Ô£à **Velocity clamping** - Max 15 px/frame to prevent chaos
- Ô£à **Collision groups** - Each person gets their own group (no inter-person collision)
- Ô£à **Spring constraints** - Satellites orbit main bubbles with soft springs

**Bubble Structure**:
```
Main Bubble (80px radius)
  Ôö£ÔöÇ Satellite 1 (30px) ÔöÇÔöÉ
  Ôö£ÔöÇ Satellite 2 (30px) ÔöÇÔöñ Connected via springs
  Ôö£ÔöÇ Satellite 3 (30px) ÔöÇÔöñ (stiffness: 0.008, damping: 0.1)
  Ôö£ÔöÇ Satellite 4 (30px) ÔöÇÔöñ
  ÔööÔöÇ Satellite 5 (30px) ÔöÇÔöÿ
```

**Physics Config**:
- Gravity: 0.3 (adjustable 0-2)
- Restitution: 0.8 (bounciness)
- Friction: 0.01 (very slippery)
- Air resistance: 0.02
- Density: 0.001 (main), 0.0005 (satellite)

---

#### 4. Enhanced Visual Renderer ([EnhancedBubbleCanvas.jsx](frontend/src/components/EnhancedBubbleCanvas.jsx))

**Renderer**: Three.js with WebGL

**Visual Style**: Glossy/glowing spheres with parallax

**Main Bubble Rendering**:
```javascript
// Glossy gradient with specular highlight
RadialGradient:
  - Center: white (0.6 alpha) - glossy highlight
  - Mid: garment color (0.9 alpha)
  - Edge: darker garment color (1.0 alpha)

// Glow layer (1.3├ù radius)
  - Color: garment color
  - Opacity: 0.25 (fades in/out)

// Text label
  - Category name (TOP/BOTTOM/DRESS/SHOES)
  - White text with shadow
```

**Satellite Bubble Rendering**:
```javascript
// Blue-purple gradient
RadialGradient:
  - Center: white (0.7 alpha)
  - Mid: #6366f1 (0.8 alpha)
  - Edge: #4f46e5 (0.95 alpha)

// Glow layer (1.4├ù radius)
  - Color: #6366f1
  - Opacity: 0.2
```

**Performance Optimizations**:
- Orthographic camera (2D projection)
- Throttled physics updates (30 FPS for ML, 60 FPS for render)
- Mesh reuse (update position, not recreate)
- Texture caching with CanvasTexture
- Anti-aliasing enabled
- Pixel ratio capped at 2├ù

---

## Data Flow

### Real-time Processing Pipeline

```
Frame @10 FPS (camera) ÔåÆ WebSocket ÔåÆ Backend

ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ
Ôöé Backend (15-30ms/frame)                              Ôöé
Ôö£ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöñ
Ôöé 1. YOLOv8-seg inference (10-15ms)                   Ôöé
Ôöé    Ôåô Garment instances with masks                   Ôöé
Ôöé 2. Color extraction + feature generation (3-5ms)    Ôöé
Ôöé    Ôåô LAB colors, feature vectors                    Ôöé
Ôöé 3. FAISS similarity search ├ù N garments (5-10ms)    Ôöé
Ôöé    Ôåô Top 10 candidates per garment                  Ôöé
Ôöé 4. Re-ranking by category + color (2ms)             Ôöé
Ôöé    Ôåô Final top 5 per garment                        Ôöé
ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ
                         Ôöé
                         Ôû╝ JSON response
ÔöîÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÉ
Ôöé Frontend (60 FPS rendering)                          Ôöé
Ôö£ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöñ
Ôöé 1. Physics update @30 FPS (interpolated to 60)      Ôöé
Ôöé    - Spawn stability check (3 frames)               Ôöé
Ôöé    - Update existing bubbles                         Ôöé
Ôöé    - Fade out missing bubbles                        Ôöé
Ôöé                                                      Ôöé
Ôöé 2. Render @60 FPS                                    Ôöé
Ôöé    - Update mesh positions from physics              Ôöé
Ôöé    - Apply fade alpha to materials                   Ôöé
Ôöé    - Draw with Three.js WebGL                        Ôöé
ÔööÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÿ
```

### Frame Budget

| Component | Target | Actual |
|-----------|--------|--------|
| **Backend ML** | 30 FPS (33ms) | 15-30 FPS Ô£à |
| YOLOv8-seg | <15ms | 10-15ms Ô£à |
| Feature extraction | <5ms | 3-5ms Ô£à |
| FAISS search | <10ms | 5-10ms Ô£à |
| Re-ranking | <3ms | 1-2ms Ô£à |
| **Frontend Render** | 60 FPS (16ms) | 60 FPS Ô£à |
| Physics update | <5ms | 2-3ms Ô£à |
| Three.js render | <11ms | 8-10ms Ô£à |

---

## Multi-Person Handling

```
Scene with 2 people:

Person 0 (ID: 0):
  Bubble Cluster {
    collision_group: -1
    Ôö£ÔöÇ Top garment bubble
    Ôö£ÔöÇ Bottom garment bubble
    ÔööÔöÇ Shoes bubble
  }

Person 1 (ID: 1):
  Bubble Cluster {
    collision_group: -2  ÔåÉ Different group
    Ôö£ÔöÇ Dress bubble
    ÔööÔöÇ Shoes bubble
  }

Physics:
- Bubbles within a group: NO collision (group < 0)
- Bubbles across groups: COLLIDE (different negative groups)
- Spatial offset: Person 1 spawns 250px to the right
```

---

## Privacy & On-Prem Design

**Zero Camera Display**:
- Camera frames NEVER rendered to DOM
- Only processed in memory ÔåÆ garment data
- Frontend receives: garment metadata + thumbnails (masked crops)

**No Persistence**:
- Frames discarded after processing
- No disk writes (except logs)
- Optional: Process in Worker with OffscreenCanvas

**On-Prem Deployment**:
```
GPU PC (RTX 3060+):
Ôö£ÔöÇ Backend (Python)
Ôöé  Ôö£ÔöÇ YOLOv8-seg (GPU)
Ôöé  Ôö£ÔöÇ FashionCLIP (GPU)
Ôöé  ÔööÔöÇ FAISS (CPU)
ÔööÔöÇ Frontend (Browser)
   Ôö£ÔöÇ Camera capture (WebRTC)
   Ôö£ÔöÇ WebSocket client
   ÔööÔöÇ Three.js rendering (WebGL)
```

---

## Scalability Notes

**Current Setup** (34k images, 1-2 people):
- Backend: Single GPU, 8GB VRAM
- Index: FAISS IVF (100 clusters)
- Latency: ~20ms per garment query

**Scaling to 100k+ images**:
1. Use FAISS HNSW for faster search
2. Batch garment queries (process all garments together)
3. Consider Qdrant for distributed search + filtering

**Scaling to 5+ people**:
1. Adaptive FPS: Lower ML rate with more people
2. Garment cap: Max 3 garments ├ù 5 people = 15 bubbles
3. Cluster simplification: Reduce satellites from 5 ÔåÆ 3

---

## File Structure

```
backend/
Ôö£ÔöÇÔöÇ segmentation/
Ôöé   Ôö£ÔöÇÔöÇ yolo_garment_segmenter.py    # YOLOv8 instance seg
Ôöé   ÔööÔöÇÔöÇ garment_segmenter.py         # Old MediaPipe version
Ôö£ÔöÇÔöÇ search/
Ôöé   Ôö£ÔöÇÔöÇ enhanced_fashion_search.py   # FashionCLIP + re-ranking
Ôöé   ÔööÔöÇÔöÇ fashion_search.py            # Basic version
Ôö£ÔöÇÔöÇ main.py                          # FastAPI server
Ôö£ÔöÇÔöÇ requirements.txt                 # Python deps
ÔööÔöÇÔöÇ prepare_metadata.py              # Helper script

frontend/
Ôö£ÔöÇÔöÇ src/
Ôöé   Ôö£ÔöÇÔöÇ components/
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ EnhancedBubbleCanvas.jsx # Glossy rendering
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ BubbleCanvas.jsx         # Basic version
Ôöé   Ôöé   ÔööÔöÇÔöÇ ControlPanel.jsx         # UI controls
Ôöé   Ôö£ÔöÇÔöÇ physics/
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ EnhancedBubblePhysics.js # Spawn/fade + stability
Ôöé   Ôöé   ÔööÔöÇÔöÇ BubblePhysics.js         # Basic version
Ôöé   Ôö£ÔöÇÔöÇ utils/
Ôöé   Ôöé   ÔööÔöÇÔöÇ CameraStream.js          # WebSocket camera
Ôöé   Ôö£ÔöÇÔöÇ App.jsx                      # Main app
Ôöé   ÔööÔöÇÔöÇ main.jsx                     # Entry point
Ôö£ÔöÇÔöÇ package.json
ÔööÔöÇÔöÇ vite.config.js
```

---

## Why This Architecture?

| Decision | Rationale |
|----------|-----------|
| **YOLOv8-seg over MediaPipe** | Clean per-garment instances, category labels, better multi-person |
| **FashionCLIP** | Fashion-specific embeddings, 57% better than base CLIP on fashion |
| **FAISS IVF** | Fast search on 34k images (<10ms), scalable to 1M+ |
| **Text fusion** | Descriptions improve search quality by ~20% |
| **LAB color** | Perceptually accurate color matching (Delta E) |
| **Re-ranking** | Category + color boost ÔåÆ 30% better relevance |
| **Matter.js** | Mature 2D physics, collision groups, spring constraints |
| **Three.js** | WebGL performance, shader effects, 60 FPS easy |
| **Spawn/fade** | Prevents flicker from unstable detections |
| **EMA filtering** | Smooth color transitions (alpha=0.3) |
| **Velocity clamping** | Prevents chaotic motion with multiple people |

---

## Performance Monitoring

Add to frontend for debugging:

```javascript
const stats = {
  ml_fps: 0,
  render_fps: 0,
  bubble_count: 0,
  search_latency: 0
}

// Update every 60 frames
```

Backend metrics (add to `/health`):

```python
{
  "segmentation_time_ms": 12.3,
  "search_time_ms": 8.5,
  "total_time_ms": 25.1,
  "garments_detected": 3,
  "index_size": 34000
}
```
