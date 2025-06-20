"""
Wildlife Detector バッチ処理モジュール
大量画像の効率的な処理を管理
"""
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import threading

# 直接統合版を使用
from wildlife_detector.core.species_detector_direct import SpeciesDetector, DetectionResult
DETECTOR_VERSION = "direct"

@dataclass
class ProcessingStats:
    """処理統計クラス"""
    
    def __init__(self):
        self.start_time = time.time()
        self.processed_images = 0
        self.successful_detections = 0
        self.failed_images = 0
        self.total_images = 0
        self.current_file = ""
        self.processing_rate = 0.0
        self.estimated_remaining = 0.0
        
    def update(self, processed: int, successful: int, failed: int, current_file: str = ""):
        """統計を更新"""
        self.processed_images = processed
        self.successful_detections = successful
        self.failed_images = failed
        self.current_file = current_file
        
        # 処理速度の計算
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.processing_rate = self.processed_images / elapsed_time
    
    def get_elapsed_time(self) -> float:
        """経過時間を取得"""
        return time.time() - self.start_time
    
    def get_processing_rate(self) -> float:
        """処理速度を取得（画像/秒）"""
        return self.processing_rate
    
    def get_eta(self) -> float:
        """残り時間の推定（秒）"""
        if self.processing_rate > 0 and self.total_images > 0:
            remaining_images = self.total_images - self.processed_images
            return remaining_images / self.processing_rate
        return 0.0
    
    def get_progress_percentage(self) -> float:
        """進捗率を取得（0-100）"""
        if self.total_images > 0:
            return (self.processed_images / self.total_images) * 100
        return 0.0

class BatchProcessor:
    """バッチ処理クラス"""
    
    def __init__(self, config=None):
        self.config = config
        self.detector = None
        self.stats = ProcessingStats()
        self.is_running = False
        self.stop_requested = False
        
        # コールバック
        self.progress_callback = None
        self.error_callback = None
        
        # ログ設定
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"BatchProcessor initialized with detector version: {DETECTOR_VERSION}")
        
        # サポートされる画像形式
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def set_progress_callback(self, callback: Callable[[float, str, ProcessingStats], None]):
        """進捗コールバックを設定"""
        self.progress_callback = callback
    
    def set_error_callback(self, callback: Callable[[str, str], None]):
        """エラーコールバックを設定"""
        self.error_callback = callback
    
    def find_images(self, folder_path: str) -> List[str]:
        """フォルダ内の画像ファイルを検索"""
        image_files = []
        
        try:
            folder = Path(folder_path)
            
            for file_path in folder.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                    image_files.append(str(file_path))
            
            self.logger.info(f"フォルダ '{folder_path}' から {len(image_files)} 個の画像を発見")
            return sorted(image_files)
            
        except Exception as e:
            self.logger.error(f"画像検索エラー: {str(e)}")
            return []
    
    def process_images(self, image_paths: List[str]) -> List[DetectionResult]:
        """画像リストをバッチ処理"""
        if not image_paths:
            self.logger.warning("処理する画像がありません")
            return []
        
        # 初期化
        self.is_running = True
        self.stop_requested = False
        self.stats = ProcessingStats()
        self.stats.total_images = len(image_paths)
        
        # 検出器の初期化
        if not self._initialize_detector():
            return []
        
        results = []
        
        try:
            # 設定から最大ワーカー数を取得
            max_workers = getattr(self.config, 'max_workers', 4) if self.config else 4
            max_workers = min(max_workers, len(image_paths))  # 画像数を超えないように
            
            self.logger.info(f"バッチ処理開始: {len(image_paths)} 画像, {max_workers} ワーカー")
            
            # マルチスレッド処理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # タスクを提出
                future_to_path = {
                    executor.submit(self._process_single_image, path): path 
                    for path in image_paths
                }
                
                # 結果を収集
                for future in as_completed(future_to_path):
                    if self.stop_requested:
                        self.logger.info("処理停止が要求されました")
                        break
                    
                    image_path = future_to_path[future]
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # 統計更新
                        processed = len(results)
                        successful = sum(1 for r in results if r.has_detections())
                        failed = processed - successful
                        
                        self.stats.update(processed, successful, failed, image_path)
                        
                        # 進捗コールバック呼び出し
                        if self.progress_callback:
                            progress = self.stats.get_progress_percentage()
                            self.progress_callback(progress, image_path, self.stats)
                        
                        self.logger.debug(f"処理完了: {os.path.basename(image_path)} "
                                        f"({processed}/{len(image_paths)})")
                        
                    except Exception as e:
                        self.logger.error(f"画像処理エラー {image_path}: {str(e)}")
                        
                        # エラーコールバック
                        if self.error_callback:
                            self.error_callback(image_path, str(e))
                        
                        # エラーでも結果を追加（空の結果）
                        results.append(DetectionResult(image_path, []))
            
            self.logger.info(f"バッチ処理完了: {len(results)} 画像処理, "
                           f"{self.stats.successful_detections} 成功, "
                           f"{self.stats.failed_images} 失敗")
            
        except Exception as e:
            self.logger.error(f"バッチ処理エラー: {str(e)}")
        
        finally:
            self.is_running = False
            self._cleanup_detector()
        
        return results
    
    def _initialize_detector(self) -> bool:
        """検出器の初期化"""
        try:
            self.detector = SpeciesDetector(self.config)
            
            if self.detector.initialize():
                self.logger.info("SpeciesNet検出器の初期化が完了しました")
                return True
            else:
                self.logger.error(f"検出器初期化失敗: {self.detector.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"検出器初期化エラー: {str(e)}")
            return False
    
    def _process_single_image(self, image_path: str) -> DetectionResult:
        """単一画像の処理"""
        try:
            if self.stop_requested:
                return DetectionResult(image_path, [])
            
            # 検出実行
            result = self.detector.detect_single_image(image_path)
            return result
            
        except Exception as e:
            self.logger.error(f"画像処理エラー {image_path}: {str(e)}")
            return DetectionResult(image_path, [])
    
    def _cleanup_detector(self):
        """検出器のクリーンアップ"""
        if self.detector:
            try:
                self.detector.cleanup()
                self.detector = None
                self.logger.info("検出器をクリーンアップしました")
            except Exception as e:
                self.logger.warning(f"検出器クリーンアップエラー: {str(e)}")
    
    def stop_processing(self):
        """処理停止要求"""
        self.stop_requested = True
        self.logger.info("処理停止が要求されました")
    
    def get_stats(self) -> ProcessingStats:
        """現在の統計を取得"""
        return self.stats
    
    def is_processing(self) -> bool:
        """処理中かどうか"""
        return self.is_running
