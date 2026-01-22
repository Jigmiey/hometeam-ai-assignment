"""
Configuration management for the viewport tracking pipeline.
"""

import configparser
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Pipeline configuration parameters."""

    # Queue settings
    queue_max_size: int
    queue_timeout: float

    # Detection settings
    detection_threshold: float
    min_motion_area: int
    gaussian_blur_size: int

    # Viewport settings
    viewport_width: int
    viewport_height: int
    smoothing_window_size: int
    smoothing_alpha: float  # For exponential moving average

    # Processing settings
    target_fps: int
    frame_resize_width: int
    frame_resize_height: int

    @classmethod
    def from_file(cls, config_path: str) -> "PipelineConfig":
        """
        Load configuration from INI file.
        
        """
        path = Path(config_path)
        if not path.exists():
            print(f"Warning: {config_path} not found. Using defaults.")
            return cls.get_defaults()
        config = configparser.ConfigParser()
        config.read(path)

        return cls(
            queue_max_size=config.getint("queues","max_size",fallback=100),
            queue_timeout=config.getfloat("queues","timeout",fallback=5.0),
            detection_threshold=config.getfloat("detection","threshold",fallback=25.0),
            min_motion_area=config.getint("detection","min_motion_area",fallback=100),
            gaussian_blur_size=config.getint("detection","gaussian_blur_size",fallback=5),
            viewport_width=config.getint("viewport","width",fallback=720),
            viewport_height=config.getint("viewport","height",fallback=480),
            smoothing_window_size=config.getint("viewport","smoothing_window_size",fallback=5),
            smoothing_alpha=config.getfloat("viewport","smoothing_alpha",fallback=0.3),
            target_fps=config.getint("processing","target_fps",fallback=5),
            frame_resize_width=config.getint("processing","frame_resize_width",fallback=1280),
            frame_resize_height=config.getint("processing","frame_resize_height",fallback=720),
        )
    
    @classmethod
    def get_defaults(cls):
        """ Helper to return hardcoded defaults"""
        print("Return hardcoded defaults")
        return cls(
            queue_max_size=100,
            queue_timeout=5.0,
            detection_threshold=25.0,
            min_motion_area=100,
            gaussian_blur_size=5,
            viewport_width=720,
            viewport_height=480,
            smoothing_window_size=5,
            smoothing_alpha=0.3,
            target_fps=5,
            frame_resize_width=1280,
            frame_resize_height=720,
        )

    def __str__(self):
        return f"PipelineConfig(queue_size={self.queue_max_size}, viewport={self.viewport_width}x{self.viewport_height})"
