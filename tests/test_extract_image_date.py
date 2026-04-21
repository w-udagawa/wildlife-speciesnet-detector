"""extract_image_date() ヘルパーのテスト"""
import os
from datetime import datetime
from pathlib import Path

from utils.image_meta import extract_image_date


def test_returns_mtime_when_no_exif(tmp_path: Path):
    img = tmp_path / "plain.jpg"
    img.write_bytes(b"not really a jpeg")

    target = datetime(2023, 6, 15, 12, 0, 0)
    os.utime(img, (target.timestamp(), target.timestamp()))

    assert extract_image_date(img) == "2023-06-15"


def test_returns_none_for_nonexistent_file(tmp_path: Path):
    assert extract_image_date(tmp_path / "does_not_exist.jpg") is None


def test_prefers_exif_datetime_over_mtime(tmp_path: Path):
    """EXIF DateTime (画像IFD) が取れればそれを優先する"""
    try:
        from PIL import Image
    except ImportError:
        import pytest
        pytest.skip("Pillow not available")

    img_path = tmp_path / "with_exif.jpg"
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))

    # 画像IFDの DateTime (tag 306) は exif[tag] で書き込める
    exif = img.getexif()
    exif[306] = "2022:03:14 09:26:53"
    img.save(img_path, exif=exif)

    # mtime は別日に
    other_dt = datetime(2099, 1, 1, 0, 0, 0)
    os.utime(img_path, (other_dt.timestamp(), other_dt.timestamp()))

    assert extract_image_date(img_path) == "2022-03-14"


def test_prefers_exif_datetime_original_over_mtime(tmp_path: Path):
    """EXIF DateTimeOriginal (ExifIFD サブディレクトリ) を正しく読み取る"""
    try:
        from PIL import Image
    except ImportError:
        import pytest
        pytest.skip("Pillow not available")

    img_path = tmp_path / "with_exif_original.jpg"
    img = Image.new("RGB", (10, 10), color=(0, 255, 0))

    # DateTimeOriginal は ExifIFD (0x8769) 配下
    exif = img.getexif()
    exif_ifd = exif.get_ifd(0x8769)
    exif_ifd[36867] = "2023:08:15 10:00:00"
    # Pillow に ExifIFD を認識させるため画像IFDの DateTime も設定
    exif[306] = "2023:08:15 10:00:00"
    img.save(img_path, exif=exif)

    other_dt = datetime(2099, 1, 1, 0, 0, 0)
    os.utime(img_path, (other_dt.timestamp(), other_dt.timestamp()))

    assert extract_image_date(img_path) == "2023-08-15"
