# pipeline/queue_manager.py
"""
Queue management for inter-process communication.
"""

import multiprocessing
from dataclasses import dataclass
from typing import Any

from config import PipelineConfig


@dataclass
class FrameData:
    """Frame data structure passed through queues."""

    frame_id: int
    frame: Any  # numpy array
    timestamp: float


@dataclass
class DetectionData:
    """Detection data structure."""

    frame_id: int
    frame: Any
    motion_boxes: list  # List of (x, y, w, h) bounding boxes


@dataclass
class ViewportData:
    """Viewport data structure."""

    frame_id: int
    frame: Any
    viewport_center: tuple  # (x, y) center coordinates
    viewport_size: tuple  # (width, height)
    motion_boxes: list # List of (x,y,w,h) bounding boxes


class QueueManager:
    """Manages all queues for the pipeline."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize queues.
        
        """
        self.config = config
        # Initialize queues
        self.raw_frames_queue = multiprocessing.Queue(maxsize=config.queue_max_size)
        self.detections_queue = multiprocessing.Queue(maxsize=config.queue_max_size)
        self.viewport_queue = multiprocessing.Queue(maxsize=config.queue_max_size)