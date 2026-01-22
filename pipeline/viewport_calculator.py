# pipeline/viewport_calculator.py
"""
Viewport calculation process with state machine and smoothing.
"""

import numpy as np
import math
import random
from multiprocessing import Process
from collections import deque
from enum import Enum
from queue import Empty, Full

from pipeline.queue_manager import DetectionData, ViewportData
from config import PipelineConfig


class ViewportState(Enum):
    """Viewport calculation states."""

    TRACKING = "tracking"  # Actively following motion
    STEADY = "steady"  # Maintaining position, minimal motion


class ViewportCalculatorProcess(Process):
    """Process that calculates viewport position with state machine and smoothing."""

    def __init__(
        self,
        input_queue,  # multiprocessing.Queue
        output_queue,  # multiprocessing.Queue
        config: PipelineConfig,
    ):
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.config = config
        self.state = ViewportState.STEADY
        self.current_viewport_center = None
        self.smoothing_buffer = deque(maxlen=config.smoothing_window_size)
        self.no_motion_count = 0
        self.steady_after_n = 3

    def calculate_roi(self, motion_boxes, frame_shape):
        """
        Calculate region of interest from motion boxes.
        Returns (x, y) center coordinates
        """
        """if not motion_boxes:
            height, width = frame_shape[:2]
            return (width // 2, height // 2)
        # pick largest motion box
        x,y,bw,bh = max(motion_boxes,key=lambda b:b[2]*b[3])
        cx,cy = x + bw//2, y+bh//2
        return (cx, cy)"""
        
        prev_center = self.current_viewport_center
        h, w = frame_shape[:2]
        if not motion_boxes:
            return prev_center if prev_center is not None else (w // 2, h // 2)

        # hyperparams (tune or move to config)
        AREA_CAP_FRAC = 0.08        # cap area to 8% of frame
        BOTTOM_IGNORE_FRAC = 0.30   # penalize bottom 25% (fisheye/ref/bench zone)
        LAMBDA_DIST = 0.6           # distance penalty weight
        GAMMA_BOTTOM = 2.5         # bottom penalty weight

        frame_area = w * h
        area_cap = AREA_CAP_FRAC * frame_area
        diag = math.hypot(w, h)

        if prev_center is None:
            prev_center = (w // 2, h // 2)

        best_score = -1e18
        best_center = prev_center

        for (x, y, bw, bh) in motion_boxes:
            area = bw * bh
            area = min(area, area_cap)  # cap huge blobs

            cx = x + bw / 2.0
            cy = y + bh / 2.0

            # distance to previous center (normalized)
            dist = math.hypot(cx - prev_center[0], cy - prev_center[1]) / (diag + 1e-9)

            # bottom penalty: boxes whose center is near bottom get penalized
            # (fisheye makes near-camera blobs huge)
            bottom_zone_start = (1.0 - BOTTOM_IGNORE_FRAC) * h
            bottom_pen = 0.0
            if cy > bottom_zone_start:
                bottom_pen = (cy - bottom_zone_start) / (h * BOTTOM_IGNORE_FRAC + 1e-9)  # 0..1

            # score: prefer area, prefer continuity, avoid bottom
            score = (area / frame_area) - (LAMBDA_DIST * dist) - (GAMMA_BOTTOM * bottom_pen)

            if score > best_score:
                best_score = score
                best_center = (int(cx), int(cy))

        return best_center

    def update_state(self, motion_boxes):
        """
        Update viewport state based on motion detection.
        
        """
        # TODO: Implement state transition logic
        if len(motion_boxes) > 0:
            self.no_motion_count =0
            self.state = ViewportState.TRACKING
        else:
            self.no_motion_count += 1
            if self.no_motion_count >= self.steady_after_n:
                self.state = ViewportState.STEADY

    def smooth_viewport(self, raw_viewport_center):
        """
        Apply smoothing to viewport position.
        Return smoothed (x, y) position
        """
        self.smoothing_buffer.append(raw_viewport_center)

        if len(self.smoothing_buffer) < 2:
            return raw_viewport_center
        
        #moving average
        xs=[p[0] for p in self.smoothing_buffer]
        ys=[p[1] for p in self.smoothing_buffer]
        smoothed = (int(sum(xs) / len(xs)), int(sum(ys) / len(ys)))
        return smoothed

    def clamp_viewport(self, viewport_center, frame_shape):
        """
        Ensure viewport stays within frame boundaries.
        Return clamped (x, y) position
        """
        x, y = viewport_center
        height, width = frame_shape[:2]
        vp_w, vp_h = self.config.viewport_width, self.config.viewport_height

        # TODO: Clamp x and y to ensure viewport fits in frame
        x = max(vp_w // 2, min(x, width - vp_w // 2))
        y = max(vp_h // 2, min(y, height - vp_h // 2))

        return (x, y)

    def run(self):
        """
        Calculate viewport positions from detection data.

        """
        print("ViewportCalculatorProcess: Starting viewport calculation")

        # Initialize viewport to center
        # TODO: Get first frame to initialize viewport center
        try:
            while True:
                try:
                    detection_data = self.input_queue.get(timeout=self.config.queue_timeout)
                except Empty:
                    continue
                if detection_data is None:
                    while True:
                        try:
                            self.output_queue.put(None,timeout=self.config.queue_timeout)
                            break
                        except Full:
                            print("ViewportCalculatorProcess: output queue full while sending sentinel, waiting...")
                    print("ViewportCalculatorProcess: Finished (received sentinel)")        
                    return
                frame_shape = detection_data.frame.shape
                viewport_size = (self.config.viewport_width, self.config.viewport_height)
                if self.current_viewport_center is None:
                    h, w = frame_shape[:2]
                    self.current_viewport_center = (w // 2, h // 2)
                    
                self.update_state(detection_data.motion_boxes)
                if self.state == ViewportState.STEADY:
                    self.smoothing_buffer.clear()
                
                if self.state == ViewportState.TRACKING:
                    raw_centre = self.calculate_roi(detection_data.motion_boxes,frame_shape)
                    clamped_centre = self.clamp_viewport(raw_centre,frame_shape)
                    smoothed_centre = self.smooth_viewport(clamped_centre)
                    clamped_centre = self.clamp_viewport(smoothed_centre,frame_shape)
                    self.current_viewport_center = clamped_centre
                
                viewport_centre = self.current_viewport_center
                
                viewport_data = ViewportData(frame_id=detection_data.frame_id,
                                             frame=detection_data.frame,
                                             viewport_center=viewport_centre,
                                             viewport_size=viewport_size,
                                             motion_boxes=detection_data.motion_boxes)
                while True:
                    try:
                        self.output_queue.put(viewport_data,timeout=self.config.queue_timeout)
                        break
                    except Full:
                        print("ViewportCalculatorProcess:outputqueue full, waiting...")
        
        except Exception as e:
            print(f"ViewportCalculator error: {e}")
            try:
                self.output_queue.put(None,timeout=self.config.queue_timeout)
            except Exception:
                pass    
            raise