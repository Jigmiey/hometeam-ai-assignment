# pipeline/output_writer.py
"""
Output writing process for visualization and video generation.
"""

import os
import cv2
import numpy as np
from multiprocessing import Process
from queue import Empty

from pipeline.queue_manager import ViewportData
from config import PipelineConfig


class OutputWriterProcess(Process):
    """Process that writes visualization and output video."""

    def __init__(
        self,
        input_queue,  # multiprocessing.Queue
        output_dir: str,
        config: PipelineConfig,
    ):
        super().__init__()
        self.input_queue = input_queue
        self.output_dir = output_dir
        self.config = config

    def run(self):
        """
        Write visualization and output video.

        """
        print("OutputWriterProcess: Starting output writing")

        # Create output directories
        frames_dir = os.path.join(self.output_dir, "frames")
        viewport_dir = os.path.join(self.output_dir, "viewport")
        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(viewport_dir, exist_ok=True)
        
        # Dimensions of output video
        height, width = self.config.frame_resize_height, self.config.frame_resize_width
        vp_h, vp_w = self.config.viewport_height, self.config.viewport_width

        # Initialize video writers
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_path = os.path.join(self.output_dir,"motion_detected.mp4")
        video_writer = cv2.VideoWriter(video_path,fourcc,self.config.target_fps,(width,height))
        
        viewport_path = os.path.join(self.output_dir,"viewport_view.mp4")
        viewport_writer = cv2.VideoWriter(viewport_path,fourcc,self.config.target_fps,(vp_w,vp_h))

        try:
            while True:
                try:
                    viewport_data = self.input_queue.get(timeout=self.config.queue_timeout)
                except Empty:
                    continue   
                if viewport_data is None:
                    print("VideoWriter: Finished (received sentinel)")
                    return
                frame_id,frame,viewport_center,viewport_size = viewport_data.frame_id,viewport_data.frame,viewport_data.viewport_center,viewport_data.viewport_size
                
                # Draw viewport rectangle
                x,y = viewport_center
                vp_width, vp_height = viewport_size 
                x1,y1,x2,y2 = int(x-vp_width/2),int(y-vp_height/2), int(x + vp_width/2), int(y + vp_height/2)
                
                frame_copy =frame.copy()
                motion_boxes=viewport_data.motion_boxes
                for box in motion_boxes:
                    cv2.rectangle(frame_copy,(box[0],box[1]),(box[0]+box[2],box[1]+box[3]),(0,255,0),1)
                cv2.putText(img=frame_copy,text=f"Frame: {frame_id+1}", org=(10, 30),fontFace=cv2.FONT_HERSHEY_SIMPLEX,fontScale=0.8,color=(0, 255, 0),thickness=2,lineType=cv2.LINE_AA)
                cv2.rectangle(frame_copy,(x1,y1),(x2,y2),(255,0,0),2)
                
                
                # extract viewport content 
                vp_frame = frame[y1:y2,x1:x2].copy()
                cv2.putText(img=vp_frame,text=f"Frame: {frame_id}", org=(10, 30),fontFace=cv2.FONT_HERSHEY_SIMPLEX,fontScale=0.8,color=(0, 255, 0),thickness=2,lineType=cv2.LINE_AA)
                
                # saving images
                filename = os.path.join(frames_dir, f"frame_{frame_id+1:04d}.png")
                cv2.imwrite(filename,frame_copy)
                filename = os.path.join(viewport_dir, f"frame_{frame_id+1:04d}.png")
                cv2.imwrite(filename,vp_frame)
                
                # writing frames to video writers
                video_writer.write(frame_copy)
                viewport_writer.write(vp_frame)
                
        except Exception as e:
            print(f"Video Writer Error:{e}")
            raise
        
        finally:
            video_writer.release()
            viewport_writer.release()
