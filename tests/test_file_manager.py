"""FileManager のユニットテスト"""
import os
from datetime import datetime, timedelta
from pathlib import Path

from utils.file_manager import FileManager, NO_DETECTION_FOLDER, extract_image_date


class TestSafeFolderName:
    def test_invalid_chars_are_replaced(self, tmp_path: Path):
        fm = FileManager(str(tmp_path))
        name = fm._create_safe_folder_name('Foo<>:"/\\|?*Bar', "")
        for ch in '<>:"/\\|?*':
            assert ch not in name

    def test_common_and_species_combined(self, tmp_path: Path):
        fm = FileManager(str(tmp_path))
        name = fm._create_safe_folder_name("Corvus macrorhynchos", "ハシブトガラス")
        assert "ハシブトガラス" in name
        assert "Corvus macrorhynchos" in name

    def test_empty_falls_back_to_default(self, tmp_path: Path):
        fm = FileManager(str(tmp_path))
        assert fm._create_safe_folder_name("   ", "") == "Unknown_Species"

    def test_long_name_is_truncated(self, tmp_path: Path):
        fm = FileManager(str(tmp_path))
        long_name = "A" * 300
        assert len(fm._create_safe_folder_name(long_name, "")) <= 100


class TestUniqueDestination:
    def test_returns_original_when_not_exists(self, tmp_path: Path):
        fm = FileManager(str(tmp_path))
        result = fm._get_unique_destination_path(tmp_path, "new.jpg")
        assert result == tmp_path / "new.jpg"

    def test_appends_counter_on_conflict(self, tmp_path: Path):
        (tmp_path / "img.jpg").write_bytes(b"existing")
        fm = FileManager(str(tmp_path))
        result = fm._get_unique_destination_path(tmp_path, "img.jpg")
        assert result.name == "img_001.jpg"

    def test_multiple_conflicts_increment_counter(self, tmp_path: Path):
        (tmp_path / "img.jpg").write_bytes(b"0")
        (tmp_path / "img_001.jpg").write_bytes(b"1")
        (tmp_path / "img_002.jpg").write_bytes(b"2")
        fm = FileManager(str(tmp_path))
        result = fm._get_unique_destination_path(tmp_path, "img.jpg")
        assert result.name == "img_003.jpg"


class TestOrganizeImagesFromCsv:
    def _make_csv(self, csv_path: Path, rows: list[dict]) -> None:
        import csv as csv_mod
        fieldnames = [
            "image_path", "image_name", "species", "scientific_name",
            "confidence", "category", "common_name", "timestamp"
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def test_organizes_files_by_species(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        out_dir = tmp_path / "out"

        img_a = src_dir / "a.jpg"
        img_b = src_dir / "b.jpg"
        img_a.write_bytes(b"a")
        img_b.write_bytes(b"b")

        csv_path = tmp_path / "results.csv"
        self._make_csv(csv_path, [
            {"image_path": str(img_a), "image_name": "a.jpg",
             "species": "Corvus macrorhynchos", "common_name": "ハシブトガラス",
             "scientific_name": "Corvus macrorhynchos", "confidence": "0.9",
             "category": "bird", "timestamp": ""},
            {"image_path": str(img_b), "image_name": "b.jpg",
             "species": "", "common_name": "",
             "scientific_name": "", "confidence": "0",
             "category": "", "timestamp": ""},
        ])

        fm = FileManager(str(out_dir))
        result = fm.organize_images_by_species_from_csv(str(csv_path), copy_files=True)

        assert any("Corvus" in k for k in result)
        assert "未検出_No_Detection" in result
        assert img_a.exists()  # copy (not move)

    def test_blank_label_routes_to_no_detection(self, tmp_path: Path):
        """SpeciesNet の 'blank' も未検出フォルダに統一される"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        img = src_dir / "blank.jpg"
        img.write_bytes(b"b")

        out_dir = tmp_path / "out"
        csv_path = tmp_path / "results.csv"
        self._make_csv(csv_path, [
            {"image_path": str(img), "image_name": "blank.jpg",
             "species": "blank", "common_name": "blank",
             "scientific_name": "blank", "confidence": "0.99",
             "category": "no_detection", "timestamp": ""},
        ])

        fm = FileManager(str(out_dir))
        result = fm.organize_images_by_species_from_csv(str(csv_path), copy_files=True)

        assert list(result.keys()) == [NO_DETECTION_FOLDER]
        assert not (out_dir / "blank_blank").exists()

    def test_no_cv_result_routes_to_no_detection(self, tmp_path: Path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        img = src_dir / "nocv.jpg"
        img.write_bytes(b"n")

        out_dir = tmp_path / "out"
        csv_path = tmp_path / "results.csv"
        self._make_csv(csv_path, [
            {"image_path": str(img), "image_name": "nocv.jpg",
             "species": "no cv result", "common_name": "no cv result",
             "scientific_name": "no cv result", "confidence": "1.0",
             "category": "no_detection", "timestamp": ""},
        ])

        fm = FileManager(str(out_dir))
        result = fm.organize_images_by_species_from_csv(str(csv_path), copy_files=True)
        assert list(result.keys()) == [NO_DETECTION_FOLDER]

    def test_organize_by_date_creates_date_first_structure(self, tmp_path: Path):
        """organize_by_date=True で {YYYY-MM-DD}/{species}/ の日付優先構造になる"""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        img = src_dir / "a.jpg"
        img.write_bytes(b"a")

        # mtime fallback で日付を埋める
        target_dt = datetime(2024, 11, 21, 10, 30, 0)
        mtime = target_dt.timestamp()
        os.utime(img, (mtime, mtime))

        out_dir = tmp_path / "out"
        csv_path = tmp_path / "results.csv"
        self._make_csv(csv_path, [{
            "image_path": str(img), "image_name": "a.jpg",
            "species": "Corvus macrorhynchos", "common_name": "ハシブトガラス",
            "scientific_name": "Corvus macrorhynchos", "confidence": "0.9",
            "category": "bird", "timestamp": "",
        }])

        fm = FileManager(str(out_dir))
        result = fm.organize_images_by_species_from_csv(
            str(csv_path), copy_files=True, organize_by_date=True
        )

        # マップキーは "YYYY-MM-DD/species" の順
        expected_date = "2024-11-21"
        assert any(k.startswith(expected_date + "/") for k in result), f"日付→種別順になっていない: {list(result.keys())}"

        # 実ファイルは {date}/{species}/ 配下に配置
        found = list(out_dir.rglob("a.jpg"))
        assert found
        parts = found[0].relative_to(out_dir).parts
        assert parts[0] == expected_date, f"1階層目が日付になっていない: {parts}"

    def test_missing_source_is_skipped(self, tmp_path: Path):
        out_dir = tmp_path / "out"
        csv_path = tmp_path / "results.csv"
        self._make_csv(csv_path, [{
            "image_path": str(tmp_path / "nonexistent.jpg"),
            "image_name": "nonexistent.jpg",
            "species": "X", "common_name": "", "scientific_name": "X",
            "confidence": "0.5", "category": "bird", "timestamp": "",
        }])

        fm = FileManager(str(out_dir))
        result = fm.organize_images_by_species_from_csv(str(csv_path), copy_files=True)
        assert result == {}
