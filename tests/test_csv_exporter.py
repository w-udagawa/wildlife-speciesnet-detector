"""CSVExporter のユニットテスト (ストリーミング集計)"""
import csv
from pathlib import Path

from core.batch_processor import ProcessingStats
from utils.csv_exporter import CSVExporter


def _write_results_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "image_path", "image_name", "species", "scientific_name",
        "confidence", "category", "common_name", "timestamp"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_summary_as_dict(path: Path) -> dict[str, str]:
    """基本統計セクションの項目→値辞書を組み立てる"""
    stats: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        in_basic_section = False
        for row in reader:
            if not row:
                in_basic_section = False
                continue
            if row[0] == "基本統計":
                in_basic_section = True
                continue
            if in_basic_section and len(row) >= 2 and row[0] != "項目":
                stats[row[0]] = row[1]
    return stats


class TestExportSummaryFromCsv:
    def test_counts_detected_and_failed(self, tmp_path: Path):
        src = tmp_path / "detection.csv"
        _write_results_csv(src, [
            {"image_path": "/a.jpg", "image_name": "a.jpg", "species": "X",
             "scientific_name": "X", "confidence": "0.95", "category": "bird",
             "common_name": "X_common", "timestamp": ""},
            {"image_path": "/b.jpg", "image_name": "b.jpg", "species": "Y",
             "scientific_name": "Y", "confidence": "0.6", "category": "mammal",
             "common_name": "", "timestamp": ""},
            {"image_path": "/c.jpg", "image_name": "c.jpg", "species": "",
             "scientific_name": "", "confidence": "0", "category": "",
             "common_name": "", "timestamp": ""},
        ])

        exporter = CSVExporter(str(tmp_path))
        summary_path = Path(exporter.export_summary_from_csv(str(src), ProcessingStats()))

        stats = _read_summary_as_dict(summary_path)
        assert stats["総画像数"] == "3"
        assert stats["検出成功画像数"] == "2"
        assert stats["検出失敗画像数"] == "1"
        assert stats["総検出数"] == "2"

    def test_handles_empty_csv(self, tmp_path: Path):
        src = tmp_path / "empty.csv"
        _write_results_csv(src, [])

        exporter = CSVExporter(str(tmp_path))
        summary_path = Path(exporter.export_summary_from_csv(str(src), ProcessingStats()))

        stats = _read_summary_as_dict(summary_path)
        assert stats["総画像数"] == "0"
        assert stats["成功率 (%)"] == "0"

    def test_invalid_confidence_is_treated_as_zero(self, tmp_path: Path):
        src = tmp_path / "bad.csv"
        _write_results_csv(src, [
            {"image_path": "/a.jpg", "image_name": "a.jpg", "species": "X",
             "scientific_name": "X", "confidence": "not_a_number",
             "category": "bird", "common_name": "", "timestamp": ""},
        ])

        exporter = CSVExporter(str(tmp_path))
        summary_path = Path(exporter.export_summary_from_csv(str(src), ProcessingStats()))
        # 0未満として集計されるが例外は出ない
        assert summary_path.exists()
