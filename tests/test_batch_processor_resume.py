"""BatchProcessor のレジューム・CSVヘッダー・大量処理関連機能のテスト

speciesnet の実モデルは使わないため、detector をモックして検証する。
"""
import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from core.batch_processor import BatchProcessor, CSV_COLUMNS
from core.config import AppConfig
from core.species_detector_direct import DetectionResult


class FakeDetector:
    """predict_batch をモックする軽量 detector"""

    def __init__(self, config=None, raise_on_call=False):
        self.config = config
        self.is_initialized = False
        self.error_message = ""
        self.raise_on_call = raise_on_call
        self.calls = []

    def initialize(self):
        self.is_initialized = True
        return True

    def predict_batch(self, paths):
        self.calls.append(list(paths))
        if self.raise_on_call:
            raise RuntimeError("simulated API failure")
        return [
            DetectionResult(p, [{
                'species': 'Corvus', 'scientific_name': 'Corvus',
                'common_name': '', 'confidence': 0.9,
                'category': 'bird', 'bbox': []
            }])
            for p in paths
        ]

    def cleanup(self):
        self.is_initialized = False


@pytest.fixture
def tmp_images(tmp_path: Path) -> list[str]:
    """実ファイルとして存在する画像パス（extract_image_date の mtime 参照のため必要）"""
    paths = []
    src = tmp_path / "src"
    src.mkdir()
    for i in range(5):
        p = src / f"img{i}.jpg"
        p.write_bytes(b"x")
        paths.append(str(p))
    return paths


class TestResume:
    def test_skips_already_processed_paths(self, tmp_path: Path, tmp_images):
        # 事前に3枚処理済みCSVを作る
        existing = tmp_path / "existing.csv"
        with open(existing, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            for p in tmp_images[:3]:
                writer.writerow([p, Path(p).name, '2024-01-01', 'X', 'X', 0.9, 'bird', '', ''])

        processor = BatchProcessor(AppConfig())
        with patch('core.batch_processor.SpeciesDetector', lambda config: FakeDetector(config)):
            summary = processor.process_images(
                tmp_images,
                output_dir=str(tmp_path),
                resume_from_csv=str(existing),
            )

        assert summary['skipped'] == 3
        assert summary['total_processed'] == 2
        assert summary['csv_path'] == str(existing)

        # CSV に5件（既存3 + 新規2）が入っている
        with open(existing, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 5

    def test_no_existing_csv_processes_all(self, tmp_path: Path, tmp_images):
        processor = BatchProcessor(AppConfig())
        with patch('core.batch_processor.SpeciesDetector', lambda config: FakeDetector(config)):
            summary = processor.process_images(
                tmp_images,
                output_dir=str(tmp_path),
                resume_from_csv=str(tmp_path / "does_not_exist.csv"),
            )
        assert summary['skipped'] == 0
        assert summary['total_processed'] == 5


class TestConsecutiveErrors:
    def test_blank_results_do_not_increment_error_counter(self, tmp_path: Path, tmp_images):
        """検出0件が連続しても処理は止まらない（API例外のみカウント）"""
        class BlankDetector(FakeDetector):
            def predict_batch(self, paths):
                return [DetectionResult(p, []) for p in paths]  # 全て未検出

        processor = BatchProcessor(AppConfig(consecutive_error_limit=3))
        with patch('core.batch_processor.SpeciesDetector', lambda config: BlankDetector(config)):
            summary = processor.process_images(tmp_images, output_dir=str(tmp_path))

        assert summary['stopped'] is False
        assert summary['total_processed'] == 5
        assert summary['failed'] == 5  # 全て未検出だが正常完了

    def test_api_exceptions_do_increment_counter(self, tmp_path: Path, tmp_images):
        """連続チャンクで API 例外 → 上限到達で停止"""
        processor = BatchProcessor(AppConfig(
            consecutive_error_limit=2,
            predict_chunk_size=2,  # 3チャンクに分割
        ))
        with patch('core.batch_processor.SpeciesDetector',
                   lambda config: FakeDetector(config, raise_on_call=True)):
            summary = processor.process_images(tmp_images, output_dir=str(tmp_path))

        assert summary['stopped'] is True


class TestCsvHeader:
    def test_header_written_once_per_run(self, tmp_path: Path, tmp_images):
        processor = BatchProcessor(AppConfig(predict_chunk_size=2))
        with patch('core.batch_processor.SpeciesDetector', lambda config: FakeDetector(config)):
            summary = processor.process_images(tmp_images, output_dir=str(tmp_path))

        # CSV 1行目はヘッダー、以降にデータ5行 (ヘッダー重複なし)
        with open(summary['csv_path'], encoding='utf-8') as f:
            lines = f.readlines()
        assert lines[0].startswith('image_path,image_name,image_date,')
        assert lines.count(lines[0]) == 1  # ヘッダーは1行のみ

    def test_image_date_column_populated(self, tmp_path: Path, tmp_images):
        processor = BatchProcessor(AppConfig())
        with patch('core.batch_processor.SpeciesDetector', lambda config: FakeDetector(config)):
            summary = processor.process_images(tmp_images, output_dir=str(tmp_path))

        with open(summary['csv_path'], encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        # mtime fallback で全行に YYYY-MM-DD 形式の日付が入る
        for r in rows:
            assert len(r['image_date']) == 10
            assert r['image_date'][4] == '-'


class TestFindImages:
    def test_returns_case_insensitive_extensions(self, tmp_path: Path):
        # 大文字/小文字混在のファイル
        (tmp_path / "a.jpg").write_bytes(b"a")
        (tmp_path / "b.JPG").write_bytes(b"b")
        (tmp_path / "c.PnG").write_bytes(b"c")
        (tmp_path / "d.txt").write_bytes(b"d")  # 非画像

        processor = BatchProcessor(AppConfig())
        found = processor.find_images(str(tmp_path))
        names = sorted(Path(p).name for p in found)
        assert names == ['a.jpg', 'b.JPG', 'c.PnG']
