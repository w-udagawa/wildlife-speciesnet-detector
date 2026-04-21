"""振り分け進捗コールバック / パス長短縮 / CSV 内 image_date 利用 のテスト"""
import csv
from pathlib import Path

from utils.file_manager import FileManager, NO_DETECTION_FOLDER


def _write_csv(path: Path, rows: list[dict], with_date: bool = True) -> None:
    fieldnames = [
        "image_path", "image_name", "image_date",
        "species", "scientific_name", "confidence",
        "category", "common_name", "timestamp",
    ]
    if not with_date:
        fieldnames = [f for f in fieldnames if f != 'image_date']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, '') for k in fieldnames})


class TestOrganizeProgress:
    def test_progress_callback_invoked(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        rows = []
        for i in range(5):
            p = src / f"a{i}.jpg"
            p.write_bytes(b"x")
            rows.append({
                "image_path": str(p), "image_name": p.name,
                "image_date": "2024-11-21",
                "species": "X", "common_name": "", "scientific_name": "X",
                "confidence": "0.5", "category": "bird",
            })

        csv_path = tmp_path / "det.csv"
        _write_csv(csv_path, rows)

        calls: list[tuple] = []

        def cb(processed, total, current):
            calls.append((processed, total))

        fm = FileManager(str(tmp_path / "out"))
        fm.organize_images_by_species_from_csv(
            str(csv_path), copy_files=True,
            progress_callback=cb, progress_interval=2,
        )
        # 2, 4, 5 件目で呼ばれる想定
        assert len(calls) >= 2
        assert calls[-1][0] == 5  # 最終枚数で呼ばれる
        assert calls[-1][1] == 5  # 総数


class TestCachedImageDate:
    def test_uses_image_date_from_csv_when_present(self, tmp_path: Path):
        """CSV の image_date 列を優先利用して EXIF 再読込しない"""
        src = tmp_path / "src"
        src.mkdir()
        p = src / "img.jpg"
        p.write_bytes(b"x")

        # CSV には 2020-01-15 を記載（mtime とは異なる日付）
        rows = [{
            "image_path": str(p), "image_name": "img.jpg",
            "image_date": "2020-01-15",
            "species": "X", "common_name": "", "scientific_name": "X",
            "confidence": "0.9", "category": "bird",
        }]
        csv_path = tmp_path / "det.csv"
        _write_csv(csv_path, rows)

        fm = FileManager(str(tmp_path / "out"))
        result = fm.organize_images_by_species_from_csv(
            str(csv_path), copy_files=True, organize_by_date=True,
        )
        # 2020-01-15 フォルダ配下に配置されているはず
        assert any(k.startswith("2020-01-15/") for k in result), list(result.keys())

    def test_falls_back_to_exif_when_csv_lacks_date(self, tmp_path: Path):
        """旧バージョンCSV (image_date列なし) でも動作する後方互換"""
        src = tmp_path / "src"
        src.mkdir()
        p = src / "img.jpg"
        p.write_bytes(b"x")

        rows = [{
            "image_path": str(p), "image_name": "img.jpg",
            "species": "X", "common_name": "", "scientific_name": "X",
            "confidence": "0.9", "category": "bird",
        }]
        csv_path = tmp_path / "det.csv"
        _write_csv(csv_path, rows, with_date=False)

        fm = FileManager(str(tmp_path / "out"))
        result = fm.organize_images_by_species_from_csv(
            str(csv_path), copy_files=True, organize_by_date=True,
        )
        # 何らかの日付フォルダが作られる（mtime から）
        assert result
        first_key = list(result.keys())[0]
        assert "/" in first_key  # 日付/種別の階層


class TestPathLengthShortening:
    def test_long_output_path_triggers_shortening(self, tmp_path: Path):
        # 極端に長いベースパス + 深い長い種名を組み合わせて閾値超過をシミュレート
        deep_base = tmp_path / ("a" * 80) / ("b" * 80) / ("c" * 60)
        deep_base.mkdir(parents=True)

        src = tmp_path / "src"
        src.mkdir()
        p = src / "img.jpg"
        p.write_bytes(b"x")

        fm = FileManager(str(deep_base))
        # _resolve_target_folder を直接呼ぶ
        long_name = "Very_Long_Species_Name_" * 3
        target = fm._resolve_target_folder(long_name, p, organize_by_date=False)
        # 短縮が発動すると、target の末尾セグメントは元より短くなる
        last = target.name
        # ハッシュ付き短縮形は "original_abcd1234" のように _ と 8桁 hex
        if len(str(deep_base)) + len(long_name) > 240:
            assert last != long_name
            assert '_' in last
