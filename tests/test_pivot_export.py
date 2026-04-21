"""CSVExporter.export_daily_species_pivot() のテスト"""
import csv
import os
from datetime import datetime
from pathlib import Path

from core.batch_processor import ProcessingStats
from utils.csv_exporter import CSVExporter, NO_DETECTION_PIVOT_LABEL


def _write_detection_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "image_path", "image_name", "species", "scientific_name",
        "confidence", "category", "common_name", "timestamp"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _set_mtime(path: Path, year: int, month: int, day: int) -> None:
    ts = datetime(year, month, day, 12, 0, 0).timestamp()
    os.utime(path, (ts, ts))


def _read_pivot(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.reader(f))


class TestDailySpeciesPivot:
    def test_basic_layout(self, tmp_path: Path):
        # 2024-11-21 に bird(2枚) + blank(1枚)、2024-11-22 に bird(1枚)
        src = tmp_path / "src"
        src.mkdir()
        imgs = {
            "a.jpg": (2024, 11, 21),
            "b.jpg": (2024, 11, 21),
            "c.jpg": (2024, 11, 21),  # blank
            "d.jpg": (2024, 11, 22),
        }
        for name, ymd in imgs.items():
            p = src / name
            p.write_bytes(b"x")
            _set_mtime(p, *ymd)

        detection_csv = tmp_path / "det.csv"
        _write_detection_csv(detection_csv, [
            {"image_path": str(src/"a.jpg"), "image_name": "a.jpg",
             "species": "Corvus", "common_name": "ハシブトガラス",
             "scientific_name": "Corvus", "confidence": "0.9",
             "category": "bird", "timestamp": ""},
            {"image_path": str(src/"b.jpg"), "image_name": "b.jpg",
             "species": "Corvus", "common_name": "ハシブトガラス",
             "scientific_name": "Corvus", "confidence": "0.88",
             "category": "bird", "timestamp": ""},
            {"image_path": str(src/"c.jpg"), "image_name": "c.jpg",
             "species": "", "common_name": "",
             "scientific_name": "", "confidence": "0",
             "category": "", "timestamp": ""},
            {"image_path": str(src/"d.jpg"), "image_name": "d.jpg",
             "species": "Corvus", "common_name": "ハシブトガラス",
             "scientific_name": "Corvus", "confidence": "0.8",
             "category": "bird", "timestamp": ""},
        ])

        out = tmp_path / "out"
        exporter = CSVExporter(str(out))
        pivot_path = Path(exporter.export_daily_species_pivot(str(detection_csv)))

        rows = _read_pivot(pivot_path)
        assert rows[0] == ["日付", "2024-11-21", "2024-11-22"]

        # 合計撮影枚数
        assert rows[1] == ["合計撮影枚数", "3", "1"]

        # 撮影無し行
        no_det = next(r for r in rows if r[0] == NO_DETECTION_PIVOT_LABEL)
        assert no_det == [NO_DETECTION_PIVOT_LABEL, "1", "0"]

        # ハシブトガラス行
        bird = next(r for r in rows if r[0] == "ハシブトガラス")
        assert bird == ["ハシブトガラス", "2", "1"]

        # 合計行 (日付ごとの総枚数と一致)
        total = next(r for r in rows if r[0] == "合計")
        assert total == ["合計", "3", "1"]

    def test_blank_label_aggregated_to_no_detection(self, tmp_path: Path):
        """species='blank' と 空species が同じ '撮影無し' に集約される"""
        src = tmp_path / "src"
        src.mkdir()
        a = src / "a.jpg"; a.write_bytes(b"a"); _set_mtime(a, 2024, 6, 1)
        b = src / "b.jpg"; b.write_bytes(b"b"); _set_mtime(b, 2024, 6, 1)

        det = tmp_path / "det.csv"
        _write_detection_csv(det, [
            {"image_path": str(a), "image_name": "a.jpg",
             "species": "blank", "common_name": "blank",
             "scientific_name": "blank", "confidence": "0.99",
             "category": "no_detection", "timestamp": ""},
            {"image_path": str(b), "image_name": "b.jpg",
             "species": "", "common_name": "",
             "scientific_name": "", "confidence": "0",
             "category": "", "timestamp": ""},
        ])

        exporter = CSVExporter(str(tmp_path / "out"))
        pivot = Path(exporter.export_daily_species_pivot(str(det)))
        rows = _read_pivot(pivot)

        labels = [r[0] for r in rows]
        assert labels.count(NO_DETECTION_PIVOT_LABEL) == 1
        assert "blank" not in labels

        no_det = next(r for r in rows if r[0] == NO_DETECTION_PIVOT_LABEL)
        assert no_det[1] == "2"

    def test_unknown_date_sorted_last(self, tmp_path: Path):
        """取得できない日付のファイルは unknown-date 列として末尾"""
        src = tmp_path / "src"
        src.mkdir()
        ok = src / "ok.jpg"; ok.write_bytes(b"o"); _set_mtime(ok, 2024, 3, 1)
        gone = src / "gone.jpg"  # 存在しない → 日付取得不可

        det = tmp_path / "det.csv"
        _write_detection_csv(det, [
            {"image_path": str(ok), "image_name": "ok.jpg",
             "species": "X", "common_name": "", "scientific_name": "X",
             "confidence": "0.5", "category": "bird", "timestamp": ""},
            {"image_path": str(gone), "image_name": "gone.jpg",
             "species": "Y", "common_name": "", "scientific_name": "Y",
             "confidence": "0.5", "category": "bird", "timestamp": ""},
        ])

        exporter = CSVExporter(str(tmp_path / "out"))
        pivot = Path(exporter.export_daily_species_pivot(str(det)))
        rows = _read_pivot(pivot)

        header = rows[0]
        assert header[-1] == "unknown-date"
