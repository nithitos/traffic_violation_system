"""
Computer Vision & AI Video Processing Package
Includes YOLO vehicle detection, speed calculation, virtual lines, and ANPR plate recognition.
"""
from .plate_reader import PlateReader
from .video_processor import VideoTrafficProcessor

__all__ = ["PlateReader", "VideoTrafficProcessor"]
