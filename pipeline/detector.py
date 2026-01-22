"""
Motion detection process.
"""

import cv2
import numpy as np
from multiprocessing import Process
from typing import Optional
from queue import Empty,Full

from pipeline.queue_manager import FrameData, DetectionData
from config import PipelineConfig


class DetectionProcess(Process):
    """Process that detects motion in frames."""

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
        self.prev_frame = None

    def run(self):
        """
        Detect motion in frames from input queue.
        
        """
        print("DetectionProcess: Starting motion detection")
        prev_frame_gray_blurred = None
        
        k = int(self.config.gaussian_blur_size)
        if k % 2 == 0:
            k += 1
        if k < 3:
            k = 3
        try:
            while True:
                try:
                    frame_data = self.input_queue.get(timeout=self.config.queue_timeout)
                except Empty:
                    continue
                if frame_data is None:  # End of stream
                    while True:
                        try:
                            self.output_queue.put(None,timeout=self.config.queue_timeout)
                            break
                        except Full:
                            print("DetectionProcess: output queue full while sending sentinel, waiting...")
                    print("DetectionProcess: Finished (received sentinel)")
                    return
                # Detect motion and queue results
                current_frame = frame_data.frame
                current_frame_gray = cv2.cvtColor(current_frame,cv2.COLOR_BGR2GRAY)
                current_frame_gray_blurred = cv2.GaussianBlur(current_frame_gray,(k,k),0)
                if prev_frame_gray_blurred is None:
                    detection_data = DetectionData(frame_id=frame_data.frame_id,
                                               frame=frame_data.frame,
                                               motion_boxes=[]
                                               )
                else:
                    
                    # calculate absolute differecne with previous frame
                    diff_gray = cv2.absdiff(prev_frame_gray_blurred,current_frame_gray_blurred)
                    
                    # apply threshold
                    _, thresh = cv2.threshold(diff_gray,self.config.detection_threshold,255,cv2.THRESH_BINARY)
                    
                    # dilate thresh to fill in holes
                    dilated = cv2.dilate(thresh,None,iterations=3)
                    
                    # find contours and extract bounding box
                    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    motion_boxes = []
                    for contour in contours:
                        if cv2.contourArea(contour) < self.config.min_motion_area:
                            continue
                        (x,y,w,h)=cv2.boundingRect(contour)
                        motion_boxes.append((x,y,w,h))
                    
                    detection_data = DetectionData(frame_id=frame_data.frame_id,
                                               frame=frame_data.frame,
                                               motion_boxes=motion_boxes
                                               )
                    
                while True:
                    try:
                        self.output_queue.put(detection_data,timeout=self.config.queue_timeout)
                        break
                    except Full:
                        print("DetectionProcess: output queue full, waiting....")
                prev_frame_gray_blurred = current_frame_gray_blurred
                
        except Exception as e:
            print(f"DetectionProcess: error:{e}")
            try:
                self.output_queue.put(None, timeout=self.config.queue_timeout)
            except Exception:
                pass
            raise
            