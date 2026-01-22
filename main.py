import os
import argparse
import multiprocessing
from pathlib import Path
import configparser

from pipeline.frame_reader import FrameReaderProcess
from pipeline.detector import DetectionProcess
from pipeline.viewport_calculator import ViewportCalculatorProcess
from pipeline.output_writer import OutputWriterProcess
from pipeline.queue_manager import QueueManager
from config import PipelineConfig


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Production-Grade Viewport Tracking System"
    )
    parser.add_argument(
        "--video", type=str, required=True, help="Path to input video file"
    )
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument(
        "--config",
        type=str,
        default="config.ini",
        help="Path to configuration file",
    )
    return parser.parse_args()


def main():
    """Main function to run the viewport tracking pipeline."""
    args = parse_args()

    # Load configuration
    config = PipelineConfig.from_file(args.config)

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    print(f"Starting viewport tracking pipeline for: {args.video}")
    print(f"Configuration: {config}")

    # Initialize queue manager
    queue_manager = QueueManager(config)

    # Create processes
    processes = []

    # Frame Reader Process
    frame_reader = FrameReaderProcess(
        input_video=args.video,
        output_queue=queue_manager.raw_frames_queue,
        config=config,
    )
    processes.append(frame_reader)

    # Detection Process
    detector = DetectionProcess(
        input_queue=queue_manager.raw_frames_queue,
        output_queue=queue_manager.detections_queue,
        config=config,
    )
    processes.append(detector)

    # Viewport Calculator Process
    viewport_calculator = ViewportCalculatorProcess(
        input_queue=queue_manager.detections_queue,
        output_queue=queue_manager.viewport_queue,
        config=config,
    )
    processes.append(viewport_calculator)

    # Output Writer Process
    output_writer = OutputWriterProcess(
        input_queue=queue_manager.viewport_queue,
        output_dir=args.output,
        config=config,
    )
    processes.append(output_writer)

    # Start all processes
    try:
        for process in processes:
            process.start()
            print(f"Started process: {process.__class__.__name__}")

        # Wait for all processes to complete
        for process in processes:
            process.join()
            print(f"Completed process: {process.__class__.__name__}")

    except KeyboardInterrupt:
        print("\nShutting down pipeline...")
        for process in processes:
            process.terminate()
            process.join()
    except Exception as e:
        print(f"Error in pipeline: {e}")
        for process in processes:
            process.terminate()
            process.join()
        raise

    print(f"Pipeline complete. Results saved to {args.output}")


if __name__ == "__main__":
    main()