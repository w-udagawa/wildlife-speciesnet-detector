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
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime

# 直接統合版を使用
from core.species_detector_direct import SpeciesDetector, DetectionResult
DETECTOR_VERSION = "native"


def _get_extract_image_date():
    """utils.image_meta.extract_image_date を遅延インポート（循環import回避）"""
    from utils.image_meta import extract_image_date
    return extract_image_date

# 結果CSVのカラム定義（image_date 列を含む最新バージョン）
CSV_COLUMNS = [
    'image_path', 'image_name', 'image_date',
    'species', 'scientific_name', 'confidence',
    'category', 'common_name', 'timestamp'
]

# 進捗コールバックのスロットリング間隔
_PROGRESS_THROTTLE_IMAGES = 20   # N枚毎
_PROGRESS_THROTTLE_SECONDS = 0.5  # または N秒毎（先に到達した方）

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
        self.consecutive_errors = 0  # API例外（predict_batch失敗）の連続回数。検出0件では加算しない
        self.skipped_images = 0       # レジューム時にスキップした枚数

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
        self.predict_chunk_size = getattr(config, 'predict_chunk_size', 500) if config else 500

        # 結果CSV保存パス
        self.intermediate_save_path = None

        # CSVヘッダー書込み済みフラグ（file_exists判定に依存しない）
        self._csv_header_written = False

        # 進捗コールバックのスロットリング用
        self._last_progress_emit_ts = 0.0
        self._last_progress_emit_count = 0

    def set_progress_callback(self, callback: Callable[[float, str, ProcessingStats], None]):
        """進捗コールバックを設定"""
        self.progress_callback = callback

    def set_error_callback(self, callback: Callable[[str, str], None]):
        """エラーコールバックを設定"""
        self.error_callback = callback

    def find_images(self, folder_path: str) -> List[str]:
        """フォルダ内の画像ファイルを検索（単一rglob走査 + 拡張子set判定）"""
        try:
            folder = Path(folder_path)
            exts = self.supported_extensions
            image_files = [
                str(p) for p in folder.rglob('*')
                if p.is_file() and p.suffix.lower() in exts
            ]
            image_files.sort()
            self.logger.info(f"フォルダ '{folder_path}' から {len(image_files)} 個の画像を発見")
            return image_files

        except OSError as e:
            self.logger.error(f"画像検索エラー: {e}")
            return []

    @staticmethod
    def load_processed_paths(csv_path: Path) -> Set[str]:
        """既存の結果CSVから処理済みパスを読み出す（レジューム用）"""
        processed: Set[str] = set()
        if not csv_path.exists():
            return processed
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    p = (row.get('image_path') or '').strip()
                    if p:
                        processed.add(p)
        except OSError:
            return set()
        return processed

    def process_images(self, image_paths: List[str], output_dir: Optional[str] = None,
                       resume_from_csv: Optional[str] = None) -> Dict[str, Any]:
        """画像リストをバッチ処理（チャンク単位ネイティブAPIバッチ版）

        Args:
            image_paths: 処理対象の画像パスリスト
            output_dir: 中間CSV保存先ディレクトリ
            resume_from_csv: 指定した既存CSVに記載のあるパスをスキップして追記する
                （1万枚中5千枚まで処理済みだった場合などの再開用）

        Returns:
            Dict[str, Any]: 処理サマリー情報
                - total_processed: 処理画像数（このランで処理した枚数）
                - successful: 検出成功数
                - failed: 検出失敗数
                - skipped: レジュームでスキップした枚数
                - csv_path: 結果CSVパス
                - stopped: 処理が中断されたか
        """
        if not image_paths:
            self.logger.warning("処理する画像がありません")
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'skipped': 0,
                    'csv_path': None, 'stopped': False}

        # レジューム: 既存CSVから処理済みパスを除外
        total_skipped = 0
        resume_csv_path: Optional[Path] = None
        if resume_from_csv:
            resume_csv_path = Path(resume_from_csv)
            processed_paths = self.load_processed_paths(resume_csv_path)
            if processed_paths:
                pending = [p for p in image_paths if p not in processed_paths]
                total_skipped = len(image_paths) - len(pending)
                self.logger.info(f"レジューム: 既存CSV({resume_csv_path.name})の {len(processed_paths)} 件を参照し、"
                                 f"{total_skipped} 枚スキップ / {len(pending)} 枚を処理対象に")
                image_paths = pending
            else:
                self.logger.info(f"レジューム: 既存CSV {resume_csv_path} から処理済みパスを読めず、全件処理します")

        if not image_paths:
            self.logger.info("レジューム後に処理対象が残っていません")
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'skipped': total_skipped,
                    'csv_path': str(resume_csv_path) if resume_csv_path and resume_csv_path.exists() else None,
                    'stopped': False}

        # 初期化
        self.is_running = True
        self.stop_requested = False
        self.stats = ProcessingStats()
        self.stats.total_images = len(image_paths)
        self.stats.skipped_images = total_skipped
        self._csv_header_written = False
        self._last_progress_emit_ts = 0.0
        self._last_progress_emit_count = 0

        # 中間保存パスの設定（レジューム時は既存CSVに追記）
        if resume_csv_path and resume_csv_path.exists():
            self.intermediate_save_path = resume_csv_path
            self._csv_header_written = True  # 既存CSVにヘッダーがある前提
        elif output_dir:
            self.intermediate_save_path = Path(output_dir) / f"detection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            self.intermediate_save_path = Path(f"detection_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        # 検出器の初期化
        if not self._initialize_detector():
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'skipped': total_skipped,
                    'csv_path': None, 'stopped': False}

        # ストリーミング用バッファ（メモリ解放のため）
        result_buffer = []
        total_processed = 0
        total_successful = 0
        total_failed = 0

        try:
            predict_chunk_size = self.predict_chunk_size

            self.logger.info(f"バッチ処理開始（ネイティブAPIモード）: {len(image_paths)} 画像, "
                            f"チャンクサイズ={predict_chunk_size}, 内部バッチサイズ={self.batch_size}")
            self.logger.info(f"メモリ管理: GC間隔={self.gc_interval}枚, チャンク境界で中間保存")
            self.logger.info(f"結果CSV: {self.intermediate_save_path}")

            # チャンク単位でバッチ処理
            for chunk_start in range(0, len(image_paths), predict_chunk_size):
                if self.stop_requested:
                    self.logger.info("処理停止が要求されました")
                    break

                chunk = image_paths[chunk_start:chunk_start + predict_chunk_size]
                chunk_api_failed = False

                try:
                    chunk_results = self.detector.predict_batch(chunk)
                except Exception:
                    self.logger.exception("チャンクバッチ処理エラー（API例外）")
                    chunk_results = [DetectionResult(p, []) for p in chunk]
                    chunk_api_failed = True

                # API例外時のみ連続エラーカウンタを加算（検出0件は加算しない）
                if chunk_api_failed:
                    self.stats.consecutive_errors += 1
                else:
                    self.stats.consecutive_errors = 0

                # 結果処理
                for result in chunk_results:
                    if self.stop_requested:
                        break

                    result_buffer.append(result)
                    total_processed += 1

                    if result.has_detections():
                        total_successful += 1
                    else:
                        total_failed += 1

                    self.stats.update(total_processed, total_successful, total_failed, result.image_path)

                    # 進捗コールバック（スロットリング）
                    self._maybe_emit_progress(result.image_path)

                # 連続エラーチェック（チャンク終了時）
                if self.stats.consecutive_errors >= self.consecutive_error_limit:
                    self.logger.error(
                        f"API例外が連続{self.consecutive_error_limit}チャンクに達したため処理を中断"
                    )
                    self.stop_requested = True

                # チャンク境界で必ず中間保存 + メモリ解放（クラッシュ耐性向上）
                if result_buffer:
                    self._save_buffer_to_csv(result_buffer)
                    result_buffer = []
                    gc.collect()
                    self.logger.info(f"チャンク完了・中間保存 (処理済み: {total_processed}/{len(image_paths)}枚)")

            # 残りのバッファを保存
            if result_buffer:
                self._save_buffer_to_csv(result_buffer, final=True)
                result_buffer = []

            # 最後に必ず進捗コールバック（スロットリングで飛ばされている可能性があるため）
            if self.progress_callback and total_processed > 0:
                self.progress_callback(self.stats.get_progress_percentage(),
                                       self.stats.current_file, self.stats)

            self.logger.info(f"バッチ処理完了: {total_processed} 画像処理, "
                            f"{total_successful} 成功, "
                            f"{total_failed} 失敗, "
                            f"{total_skipped} スキップ")

        except Exception:
            self.logger.exception("バッチ処理エラー")
            # エラー時も残りのバッファを保存
            if result_buffer:
                try:
                    self._save_buffer_to_csv(result_buffer, final=True)
                except Exception:
                    self.logger.exception("バッチ処理エラー発生後の中間保存にも失敗")

        finally:
            self.is_running = False
            self._cleanup_detector()
            gc.collect()

        # サマリー情報を返す（メモリ節約のため全結果は返さない）
        return {
            'total_processed': total_processed,
            'successful': total_successful,
            'failed': total_failed,
            'skipped': total_skipped,
            'csv_path': str(self.intermediate_save_path) if self.intermediate_save_path.exists() else None,
            'stopped': self.stop_requested
        }

    def _maybe_emit_progress(self, current_file: str) -> None:
        """進捗コールバックをスロットリング付きで発火"""
        if not self.progress_callback:
            return
        now = time.time()
        processed = self.stats.processed_images
        images_since = processed - self._last_progress_emit_count
        seconds_since = now - self._last_progress_emit_ts

        if (images_since >= _PROGRESS_THROTTLE_IMAGES
                or seconds_since >= _PROGRESS_THROTTLE_SECONDS):
            self._last_progress_emit_count = processed
            self._last_progress_emit_ts = now
            self.progress_callback(self.stats.get_progress_percentage(),
                                   current_file, self.stats)

    def _save_buffer_to_csv(self, buffer: List[DetectionResult], final: bool = False):
        """バッファ内の結果をCSVに保存（ストリーミング用、image_date 列含む）"""
        if not buffer:
            return

        extract_image_date = _get_extract_image_date()
        try:
            mode = 'a' if self._csv_header_written else 'w'
            with open(self.intermediate_save_path, mode, newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # ヘッダー（初回のみ、フラグで明示管理）
                if not self._csv_header_written:
                    writer.writerow(CSV_COLUMNS)
                    self._csv_header_written = True

                for result in buffer:
                    # EXIF/mtime からの日付取得（処理パイプラインで1回だけ）
                    image_date = extract_image_date(Path(result.image_path)) or ''

                    if result.has_detections():
                        best = result.get_best_detection()
                        writer.writerow([
                            result.image_path,
                            result.image_name,
                            image_date,
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
                            image_date,
                            '', '', 0, '', '',
                            result.timestamp.isoformat()
                        ])

            save_type = "最終" if final else "中間"
            self.logger.info(f"{save_type}結果保存: {self.intermediate_save_path} ({len(buffer)}件追加)")

        except OSError:
            self.logger.exception("結果保存エラー")

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
