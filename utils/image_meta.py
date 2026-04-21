"""画像メタデータ抽出ユーティリティ

EXIF から撮影日を取り出す関数を提供。file_manager / batch_processor /
csv_exporter の複数モジュールから共通利用できるよう切り出した。
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

# EXIF tag ids: DateTimeOriginal/DateTimeDigitized は ExifIFD (0x8769) 配下
_EXIF_IFD_POINTER = 0x8769
_TAG_DATETIME_ORIGINAL = 36867
_TAG_DATETIME_DIGITIZED = 36868
_TAG_DATETIME = 306  # 画像IFDの DateTime


def _parse_exif_datetime(raw: object) -> Optional[str]:
    """EXIF 日時文字列 "YYYY:MM:DD HH:MM:SS" を "YYYY-MM-DD" に変換"""
    if not raw:
        return None
    date_part = str(raw).split(' ', 1)[0].replace(':', '-')
    if len(date_part) == 10 and date_part[4] == '-' and date_part[7] == '-':
        return date_part
    return None


def extract_image_date(image_path: Path) -> Optional[str]:
    """画像の撮影日を YYYY-MM-DD で返す。

    優先度: EXIF DateTimeOriginal → DateTimeDigitized → DateTime → ファイル mtime。
    読み取れない場合は None。
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            exif = img.getexif() if hasattr(img, 'getexif') else None
            if exif:
                try:
                    exif_ifd = exif.get_ifd(_EXIF_IFD_POINTER)
                except Exception:
                    exif_ifd = {}

                for tag in (_TAG_DATETIME_ORIGINAL, _TAG_DATETIME_DIGITIZED):
                    result = _parse_exif_datetime(exif_ifd.get(tag))
                    if result:
                        return result

                result = _parse_exif_datetime(exif.get(_TAG_DATETIME))
                if result:
                    return result
    except Exception:
        # Pillow 未対応形式や破損ファイルは mtime fallback で継続
        pass

    try:
        mtime = image_path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except OSError:
        return None
