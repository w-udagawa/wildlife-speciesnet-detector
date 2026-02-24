"""
Wildlife Detector バッチ処理モジュール

大量画像の効率的なバッチ処理を管理します。
SpeciesNetネイティブAPIのバッチ推論を活用し、チャンク単位で処理します。
ストリーミング処理パターンにより、数万枚の画像でもメモリ使用量を一定に保ちます。

主要クラス:
    - ProcessingStats: 処理統計情報を管理
    - BatchProcessor: バッチ処理の実行を管理

機能:
    - チャンク単位のネイティブAPIバッチ処理
    - 中間結果のCSV保存とメモリ解放
    - 連続エラー時の自動中断
    - 進捗コールバックによるUI連携

改善履歴:
    v1.0: 初期実装
    v1.1: メモリ管理強化（gc.collect()、中間結果保存）
    v1.2: ストリーミング処理パターン導入
    v2.0: ネイティブAPIバッチ処理化（ThreadPoolExecutor廃止）
"""
import os
import gc
import csv
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# 直接統合版を使用
from core.species_detector_direct import SpeciesDetector, DetectionResult
DETECTOR_VERSION = "native"

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
        self.batch_size = getattr(config, 'batch_size', 32) if config else 32

        # 結果CSV保存パス
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

    def process_images(self, image_paths: List[str], output_dir: Optional[str] = None) -> Dict[str, Any]:
        """画像リストをバッチ処理（チャンク単位ネイティブAPIバッチ版）

        Returns:
            Dict[str, Any]: 処理サマリー情報
                - total_processed: 処理画像数
                - successful: 検出成功数
                - failed: 検出失敗数
                - csv_path: 結果CSVパス
                - stopped: 処理が中断されたか
        """
        if not image_paths:
            self.logger.warning("処理する画像がありません")
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'csv_path': None, 'stopped': False}

        # 初期化
        self.is_running = True
        self.stop_requested = False
        self.stats = ProcessingStats()
        self.stats.total_images = len(image_paths)

        # 中間保存パスの設定
        if output_dir:
            self.intermediate_save_path = Path(output_dir) / f"detection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            self.intermediate_save_path = Path(f"detection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        # 検出器の初期化
        if not self._initialize_detector():
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'csv_path': None, 'stopped': False}

        # ストリーミング用バッファ（メモリ解放のため）
        result_buffer = []
        total_processed = 0
        total_successful = 0
        total_failed = 0

        try:
            batch_size = self.batch_size

            self.logger.info(f"バッチ処理開始（ネイティブAPIモード）: {len(image_paths)} 画像, バッチサイズ={batch_size}")
            self.logger.info(f"メモリ管理: GC間隔={self.gc_interval}枚, 中間保存間隔={self.intermediate_save_interval}枚")
            self.logger.info(f"結果CSV: {self.intermediate_save_path}")

            # チャンク単位でバッチ処理
            for chunk_start in range(0, len(image_paths), batch_size):
                if self.stop_requested:
                    self.logger.info("処理停止が要求されました")
                    break

                chunk = image_paths[chunk_start:chunk_start + batch_size]

                try:
                    chunk_results = self.detector.predict_batch(chunk)
                except Exception as e:
                    self.logger.error(f"チャンクバッチ処理エラー: {e}")
                    chunk_results = [DetectionResult(p, []) for p in chunk]

                # 結果処理（1画像ずつ既存ロジック適用）
                for result in chunk_results:
                    if self.stop_requested:
                        break

                    result_buffer.append(result)
                    total_processed += 1

                    # 成功/失敗カウント
                    if result.has_detections():
                        total_successful += 1
                        self.stats.consecutive_errors = 0
                    else:
                        total_failed += 1
                        self.stats.consecutive_errors += 1

                    # 統計更新
                    self.stats.update(total_processed, total_successful, total_failed, result.image_path)

                    # 連続エラーチェック
                    if self.stats.consecutive_errors >= self.consecutive_error_limit:
                        self.logger.error(f"連続エラー上限({self.consecutive_error_limit}回)に到達。処理を中断します。")
                        self.stop_requested = True
                        if result_buffer:
                            self._save_buffer_to_csv(result_buffer)
                            result_buffer = []
                        break

                    # 進捗コールバック呼び出し
                    if self.progress_callback:
                        progress = self.stats.get_progress_percentage()
                        self.progress_callback(progress, result.image_path, self.stats)

                    self.logger.debug(f"処理完了: {result.image_name} "
                                     f"({total_processed}/{len(image_paths)})")

                # 中間保存 + メモリ解放
                if len(result_buffer) >= self.intermediate_save_interval:
                    self._save_buffer_to_csv(result_buffer)
                    result_buffer = []
                    gc.collect()
                    self.logger.info(f"メモリ解放実行 (処理済み: {total_processed}枚)")

            # 残りのバッファを保存
            if result_buffer:
                self._save_buffer_to_csv(result_buffer, final=True)
                result_buffer = []

            self.logger.info(f"バッチ処理完了: {total_processed} 画像処理, "
                            f"{total_successful} 成功, "
                            f"{total_failed} 失敗")

        except Exception as e:
            self.logger.error(f"バッチ処理エラー: {str(e)}")
            # エラー時も残りのバッファを保存
            if result_buffer:
                try:
                    self._save_buffer_to_csv(result_buffer, final=True)
                except Exception:
                    pass

        finally:
            self.is_running = False
            self._cleanup_detector()
            gc.collect()

        # サマリー情報を返す（メモリ節約のため全結果は返さない）
        return {
            'total_processed': total_processed,
            'successful': total_successful,
            'failed': total_failed,
            'csv_path': str(self.intermediate_save_path) if self.intermediate_save_path.exists() else None,
            'stopped': self.stop_requested
        }

    def _save_buffer_to_csv(self, buffer: List[DetectionResult], final: bool = False):
        """バッファ内の結果をCSVに保存（ストリーミング用）"""
        try:
            if not buffer:
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
                for result in buffer:
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

            save_type = "最終" if final else "中間"
            self.logger.info(f"{save_type}結果保存: {self.intermediate_save_path} ({len(buffer)}件追加)")

        except Exception as e:
            self.logger.error(f"結果保存エラー: {str(e)}")

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
