"""Wildlife Detector 動作確認スクリプト

既定のテスト画像フォルダ (C:\\Users\\AU3009\\Desktop\\test_wildlife) に対して
バッチ処理を実行し、結果CSVと統計を出力する。GUIを起動せずに実行するため
検出ロジック・CSV出力・ファイル振り分けを素早く検証できる。

使い方:
    # 既定: 最初の3枚だけ処理（初回モデルダウンロード後のスモークテスト向け）
    python scripts/smoke_test.py

    # 全画像を処理
    python scripts/smoke_test.py --all

    # 件数指定
    python scripts/smoke_test.py --limit 10

    # 別の画像フォルダを指定
    python scripts/smoke_test.py --input /path/to/images --all

出力:
    プロジェクト直下の smoke_output/ に結果CSV・振り分けフォルダを作成。
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
from pathlib import Path

# プロジェクトルートを sys.path に追加（このスクリプトを直接 python で実行可能に）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.batch_processor import BatchProcessor
from core.config import AppConfig
from utils.csv_exporter import CSVExporter
from utils.file_manager import FileManager

DEFAULT_INPUT = Path("/mnt/c/Users/AU3009/Desktop/test_wildlife")
DEFAULT_OUTPUT = PROJECT_ROOT / "smoke_output"


def main() -> int:
    parser = argparse.ArgumentParser(description="Wildlife Detector スモークテスト")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"入力画像フォルダ (既定: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"出力フォルダ (既定: {DEFAULT_OUTPUT})")
    parser.add_argument("--limit", type=int, default=3,
                        help="処理枚数上限 (既定: 3、--all指定時は無視)")
    parser.add_argument("--all", action="store_true", help="全画像を処理")
    parser.add_argument("--confidence", type=float, default=0.1,
                        help="信頼度閾値 (既定: 0.1)")
    parser.add_argument("--clean", action="store_true", help="既存の出力フォルダを削除してから実行")
    parser.add_argument("--organize", action="store_true",
                        help="検出後に種別フォルダへファイルをコピー振り分け")
    parser.add_argument("--organize-by-date", action="store_true",
                        help="--organize と併用: 種別フォルダ配下に日付サブフォルダを作成")
    parser.add_argument("--resume", type=Path, default=None,
                        help="指定した既存検出CSVから未処理分のみ処理を再開")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("smoke_test")

    if not args.input.exists():
        log.error("入力フォルダが見つかりません: %s", args.input)
        return 1

    if args.clean and args.output.exists():
        log.info("既存の出力フォルダを削除: %s", args.output)
        shutil.rmtree(args.output)

    args.output.mkdir(parents=True, exist_ok=True)

    config = AppConfig(
        confidence_threshold=args.confidence,
        predict_chunk_size=50,  # スモークテスト向けに小さめ
    )

    processor = BatchProcessor(config)

    images = processor.find_images(str(args.input))
    if not images:
        log.error("画像が見つかりません: %s", args.input)
        return 1

    if not args.all:
        images = images[: args.limit]

    log.info("=" * 60)
    log.info("スモークテスト開始")
    log.info("  入力: %s", args.input)
    log.info("  出力: %s", args.output)
    log.info("  対象画像数: %d 枚%s", len(images), " (全画像)" if args.all else "")
    log.info("  信頼度閾値: %.2f", args.confidence)
    log.info("=" * 60)

    def on_progress(progress: float, current_file: str, stats) -> None:
        if stats.processed_images % max(1, len(images) // 10) == 0 or stats.processed_images == len(images):
            log.info("  進捗 %5.1f%% (%d/%d) %s",
                     progress, stats.processed_images, len(images),
                     Path(current_file).name)

    processor.set_progress_callback(on_progress)

    resume_path = str(args.resume) if args.resume else None
    start = time.time()
    summary = processor.process_images(images, str(args.output), resume_from_csv=resume_path)
    elapsed = time.time() - start

    log.info("=" * 60)
    log.info("処理完了")
    log.info("  経過時間: %.1f 秒 (%.2f 画像/秒)",
             elapsed, len(images) / elapsed if elapsed > 0 else 0.0)
    log.info("  処理画像数: %d", summary.get("total_processed", 0))
    log.info("  検出成功: %d", summary.get("successful", 0))
    log.info("  検出失敗: %d", summary.get("failed", 0))
    log.info("  スキップ: %d (レジューム)", summary.get("skipped", 0))
    log.info("  中断: %s", summary.get("stopped", False))
    log.info("  結果CSV: %s", summary.get("csv_path"))
    log.info("=" * 60)

    if summary.get("csv_path"):
        # ピボットCSVを常に出力（日付×撮影種の枚数集計）
        exporter = CSVExporter(str(args.output))
        pivot_path = exporter.export_daily_species_pivot(summary["csv_path"])
        log.info("日付×種別ピボット: %s", pivot_path)

    if args.organize and summary.get("csv_path"):
        organize_dir = args.output / "organized"
        organize_dir.mkdir(parents=True, exist_ok=True)
        fm = FileManager(str(organize_dir))
        org = fm.organize_images_by_species_from_csv(
            summary["csv_path"],
            copy_files=True,
            organize_by_date=args.organize_by_date,
        )
        log.info("振り分け結果: %d フォルダ作成 (出力先: %s)", len(org), organize_dir)
        for folder, files in sorted(org.items()):
            log.info("  %3d 枚: %s", len(files), folder)

    return 0


if __name__ == "__main__":
    sys.exit(main())
