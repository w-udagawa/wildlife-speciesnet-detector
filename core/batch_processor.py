"""
Wildlife Detector バッチ処理モジュール
大量画像の効率的な処理を管理

改善履歴:
- メモリ管理強化: 定期的なgc.collect()、中間結果保存
- 連続エラー時の処理中断ロジック追加
- ワーカー数削減（WSL2環境対応）
"""
import os
import gc
import csv
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import threading
from datetime import datetime

# 直接統合版を使用
from core.species_detector_direct import SpeciesDetector, DetectionResult
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
        self.consecutive_errors = 0  # 連続エラーカウンター
        self.last_intermediate_save = 0  # 最後の中間保存時の処理枚数
        
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

        # メモリ管理設定（configから取得、なければデフォルト値）
        self.gc_interval = getattr(config, 'gc_interval', 50) if config else 50
        self.intermediate_save_interval = getattr(config, 'intermediate_save_interval', 100) if config else 100
        self.consecutive_error_limit = getattr(config, 'consecutive_error_limit', 3) if config else 3

        # 中間保存用
        self.intermediate_results = []
        self.intermediate_save_path = None
    
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
    
    def process_images(self, image_paths: List[str], output_dir: Optional[str] = None) -> List[DetectionResult]:
        """画像リストをバッチ処理（メモリ管理強化版）"""
        if not image_paths:
            self.logger.warning("処理する画像がありません")
            return []

        # 初期化
        self.is_running = True
        self.stop_requested = False
        self.stats = ProcessingStats()
        self.stats.total_images = len(image_paths)
        self.intermediate_results = []

        # 中間保存パスの設定
        if output_dir:
            self.intermediate_save_path = Path(output_dir) / f"intermediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            self.intermediate_save_path = Path(f"intermediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        # 検出器の初期化
        if not self._initialize_detector():
            return []

        results = []

        try:
            # 設定から最大ワーカー数を取得（デフォルト2に削減）
            max_workers = getattr(self.config, 'max_workers', 2) if self.config else 2
            max_workers = min(max_workers, len(image_paths))  # 画像数を超えないように

            self.logger.info(f"バッチ処理開始: {len(image_paths)} 画像, {max_workers} ワーカー")
            self.logger.info(f"メモリ管理: GC間隔={self.gc_interval}枚, 中間保存間隔={self.intermediate_save_interval}枚")

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

                        # 連続エラーリセット（成功時）
                        if result.has_detections():
                            self.stats.consecutive_errors = 0
                        else:
                            self.stats.consecutive_errors += 1

                        # 連続エラーチェック
                        if self.stats.consecutive_errors >= self.consecutive_error_limit:
                            self.logger.error(f"連続エラー上限({self.consecutive_error_limit}回)に到達。処理を中断します。")
                            self.stop_requested = True
                            break

                        # 定期的なガベージコレクション
                        if processed % self.gc_interval == 0:
                            self._manage_memory(processed)

                        # 中間保存
                        if processed % self.intermediate_save_interval == 0:
                            self._save_intermediate_results(results)

                        # 進捗コールバック呼び出し
                        if self.progress_callback:
                            progress = self.stats.get_progress_percentage()
                            self.progress_callback(progress, image_path, self.stats)

                        self.logger.debug(f"処理完了: {os.path.basename(image_path)} "
                                         f"({processed}/{len(image_paths)})")

                    except Exception as e:
                        self.logger.error(f"画像処理エラー {image_path}: {str(e)}")
                        self.stats.consecutive_errors += 1

                        # 連続エラーチェック
                        if self.stats.consecutive_errors >= self.consecutive_error_limit:
                            self.logger.error(f"連続エラー上限({self.consecutive_error_limit}回)に到達。処理を中断します。")
                            self.stop_requested = True
                            break

                        # エラーコールバック
                        if self.error_callback:
                            self.error_callback(image_path, str(e))

                        # エラーでも結果を追加（空の結果）
                        results.append(DetectionResult(image_path, []))

            # 最終保存
            if results:
                self._save_intermediate_results(results, final=True)

            self.logger.info(f"バッチ処理完了: {len(results)} 画像処理, "
                            f"{self.stats.successful_detections} 成功, "
                            f"{self.stats.failed_images} 失敗")

        except Exception as e:
            self.logger.error(f"バッチ処理エラー: {str(e)}")

        finally:
            self.is_running = False
            self._cleanup_detector()
            # 最終ガベージコレクション
            gc.collect()

        return results

    def _manage_memory(self, processed_count: int):
        """メモリ管理（定期的なガベージコレクション）"""
        gc.collect()
        self.logger.info(f"メモリ解放実行 (処理済み: {processed_count}枚)")

    def _save_intermediate_results(self, results: List[DetectionResult], final: bool = False):
        """中間結果をCSVに保存"""
        try:
            # 前回保存以降の新しい結果のみを取得
            start_idx = self.stats.last_intermediate_save
            new_results = results[start_idx:]

            if not new_results:
                return

            # CSVに追記
            file_exists = self.intermediate_save_path.exists()
            mode = 'a' if file_exists else 'w'

            with open(self.intermediate_save_path, mode, newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # ヘッダー（新規ファイルの場合のみ）
                if not file_exists:
                    writer.writerow([
                        'image_path', 'image_name', 'species', 'scientific_name',
                        'confidence', 'category', 'common_name', 'timestamp'
                    ])

                # データ書き込み
                for result in new_results:
                    if result.has_detections():
                        best = result.get_best_detection()
                        writer.writerow([
                            result.image_path,
                            result.image_name,
                            best.get('species', ''),
                            best.get('scientific_name', ''),
                            best.get('confidence', 0),
                            best.get('category', ''),
                            best.get('common_name', ''),
                            result.timestamp.isoformat()
                        ])
                    else:
                        writer.writerow([
                            result.image_path,
                            result.image_name,
                            '', '', 0, '', '',
                            result.timestamp.isoformat()
                        ])

            self.stats.last_intermediate_save = len(results)
            save_type = "最終" if final else "中間"
            self.logger.info(f"{save_type}結果保存: {self.intermediate_save_path} ({len(new_results)}件追加)")

        except Exception as e:
            self.logger.error(f"中間結果保存エラー: {str(e)}")
    
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
