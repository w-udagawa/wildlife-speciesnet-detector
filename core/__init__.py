"""
Wildlife Detector コアモジュール
検出エンジン、バッチ処理、設定管理を提供
"""

from .species_detector_direct import SpeciesDetector, SpeciesDetectorDirect, DetectionResult
from .batch_processor import BatchProcessor, ProcessingStats
from .config import ConfigManager, AppConfig

__all__ = [
    'SpeciesDetector',
    'SpeciesDetectorDirect',
    'DetectionResult',
    'BatchProcessor',
    'ProcessingStats',
    'ConfigManager',
    'AppConfig',
]
