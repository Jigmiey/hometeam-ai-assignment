# Viewport Tracking System

<p align="center">
  <img src="output/motion_detected.gif" alt="Motion Detection Demo" width="100%" height=400>
</p>

## Overview

This system processes video frames through a multiprocessing pipeline to detect motion, calculate intelligent viewport positioning using a state machine, and produce visualization outputs. The implementation prioritizes system design, robustness, and production readiness.

## Architecture

The pipeline consists of four independent processes connected via bounded queues:

```
FrameReader → DetectionProcess → ViewportCalculator → OutputWriter
```

Each stage runs in its own process using Python multiprocessing, enabling:

- **Parallel execution** across CPU cores
- **Failure isolation** between pipeline stages
- **Natural backpressure** via bounded queues

### Key Data Structures

- **FrameData**: Raw frame and metadata
- **DetectionData**: Motion bounding boxes
- **ViewportData**: Viewport center and size

Sentinel values (`None`) are propagated through the pipeline to ensure graceful shutdown.

## Pipeline Stages

### 1. Frame Reader
- Reads video using OpenCV
- Downsamples to configurable target FPS
- Resizes frames to fixed resolution
- Pushes frames into bounded queue with timeout handling

### 2. Motion Detection
- Frame differencing on grayscale, blurred frames
- Thresholding and dilation for noise reduction
- Contour extraction with minimum area filtering

**Key considerations**:
- Gaussian blur kernel enforced to be odd and ≥ 3
- Bounded queues prevent unbounded memory growth
- First frame intentionally produces no detections

### 3. Viewport Calculation (State Machine)

Viewport behavior is governed by a simple state machine:

- **TRACKING**: Motion detected → actively update viewport
- **STEADY**: No motion → maintain previous viewport center

This prevents jitter and preserves temporal continuity.

#### ROI Selection Strategy

To handle fisheye distortion and false motion near the camera:

- Large blobs are capped by area
- Motion near bottom of frame is penalized
- Distance from previous viewport center is penalized

This avoids snapping to referees, benches, or near-camera artifacts.

#### Smoothing

A moving average filter is applied to viewport center coordinates to reduce jerky motion.

### 4. Output Writer
- Draws viewport rectangle on original frames
- Crops and saves viewport frames
- Writes two output videos:
  - Full frame with viewport overlay
  - Cropped viewport view

## Configuration

All tunable parameters are loaded from `config.ini`, including:

- Queue sizes and timeouts
- Detection thresholds
- Viewport size
- Smoothing parameters
- Target FPS and resize dimensions

This allows behavior changes without modifying code.

### Running Locally

Run the pipeline directly:

```bash
python main.py --video "input/sample_video_clip.mp4" --output output --config config.ini
```

Outputs are written to:

```
output/
├── motion_detected.mp4
├── viewport_view.mp4
├── frames/
└── viewport/
```

### Running with Docker

Build the image:

```bash
docker build -t viewport-tracker .
```

Run with Docker Compose:

```bash
docker compose up --build
```

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Fisheye distortion causing false large motion | Area capping, bottom-frame penalties, temporal continuity scoring |
| Viewport jitter | State machine (TRACKING vs STEADY) + moving average smoothing |
| Clean shutdown across processes | Sentinel propagation with timeout-aware queue operations |

## Future Improvements

- Optical flow-based motion estimation
- Player detection using lightweight CNN or VLM
- Adaptive smoothing based on motion magnitude
