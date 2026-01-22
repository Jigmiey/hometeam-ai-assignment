# pipeline/frame_reader.py
"""
Frame reading process that extracts frames from video.
"""

import cv2
import time
from multiprocessing import Process
from typing import Optional
from queue import Full

from pipeline.queue_manager import FrameData
from config import PipelineConfig



class FrameReaderProcess(Process):
    """Process that reads frames from video file."""

    def __init__(
        self,
        input_video: str,
        output_queue,  # multiprocessing.Queue
        config: PipelineConfig,
    ):
        super().__init__()
        self.input_video = input_video
        self.output_queue = output_queue
        self.config = config

    def run(self):
        """
        Read frames from video and put them in the output queue.
        
        """
        print(f"FrameReaderProcess: Starting to read {self.input_video}")

        cap = cv2.VideoCapture(self.input_video)
        
        if not cap.isOpened():
            print(f"Could not open video file: {self.input_video}")
            try:
                self.output_queue.put(None,timeout = self.config.queue_timeout)
            except Exception:
                pass
            return 
        try:
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            if not original_fps or original_fps <=0:
                original_fps = 30
            
            # calculate frame interval for target fps
            frame_interval = max(1,int(round(original_fps/self.config.target_fps)))
            print(f"FrameReader: original_fps={original_fps:.2f}, target_fps={self.config.target_fps}, interval={frame_interval}")
            frame_id = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_id % frame_interval == 0:
                    frame = cv2.resize(src=frame,
                                    dsize=(self.config.frame_resize_width,self.config.frame_resize_height),
                                    interpolation=cv2.INTER_AREA)
                    frame_data = FrameData(frame_id=frame_id,frame = frame, timestamp=frame_id/original_fps)
                    while True:
                        try:
                            self.output_queue.put(frame_data,timeout=self.config.queue_timeout)
                            break
                        except Full:
                            print("FrameReader: output queue full, waiting....")
                frame_id += 1
        finally:
            cap.release()
            try:
                self.output_queue.put(None,timeout=self.config.queue_timeout)
            except Exception:
                pass

        print("FrameReaderProcess: Finished reading frames")