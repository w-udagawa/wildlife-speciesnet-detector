"""
Wildlife Detector ファイル管理モジュール

検出結果に基づいて画像ファイルを種別フォルダに振り分けます。
CSVベースのストリーミング処理に対応し、メモリ効率を最適化しています。

主要クラス:
    - FileManager: ファイル振り分けと管理

機能:
    - 検出結果に基づく種別フォルダ作成
    - ファイルのコピー/移動
    - CSVからの直接振り分け（ストリーミング対応）
    - 振り分けサマリーの生成
"""
import os
import csv
import hashlib
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import logging

from core.species_detector_direct import DetectionResult, SpeciesDetectorDirect
from utils.image_meta import extract_image_date  # 後方互換のため公開継続

# 未検出扱いのファイルを格納するフォルダ名（CSV未検出 / blank / no cv result を統一）
NO_DETECTION_FOLDER = "未検出_No_Detection"

# Windows MAX_PATH 対策の閾値（振り分け先パスがこれを超えたら短縮を試みる）
_MAX_PATH_WARN_THRESHOLD = 240

__all__ = ['FileManager', 'NO_DETECTION_FOLDER', 'extract_image_date']


class FileManager:
    """ファイル管理クラス"""

    def __init__(self, base_output_dir: str):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def organize_images_by_species(self, results: List[DetectionResult],
                                 copy_files: bool = True,
                                 organize_by_date: bool = False) -> Dict[str, List[str]]:
        """検出結果に基づいて画像ファイルを種別フォルダに振り分け

        organize_by_date=True の場合、種別フォルダ配下に YYYY-MM-DD サブフォルダを作成。
        """
        organization_map: Dict[str, List[str]] = {}
        operation = "コピー" if copy_files else "移動"

        self.logger.info(f"ファイル{operation}による振り分けを開始...")
        
        try:
            for result in results:
                source_path = Path(result.image_path)
                
                if not source_path.exists():
                    self.logger.warning(f"ソースファイルが存在しません: {source_path}")
                    continue
                
                if result.has_detections():
                    best_detection = result.get_best_detection()
                    species_name = best_detection.get('species', '') or ''
                    common_name = best_detection.get('common_name', '') or ''

                    if (SpeciesDetectorDirect.is_no_detection_label(species_name)
                            and SpeciesDetectorDirect.is_no_detection_label(common_name)):
                        # SpeciesNet が blank/no cv result を返したケースも未検出に統一
                        folder_name = NO_DETECTION_FOLDER
                    else:
                        folder_name = self._create_safe_folder_name(species_name, common_name)
                else:
                    folder_name = NO_DETECTION_FOLDER

                # 出力フォルダの決定（日付サブフォルダを噛ませる場合あり）
                species_folder = self._resolve_target_folder(folder_name, source_path, organize_by_date)
                species_folder.mkdir(parents=True, exist_ok=True)

                # ファイル名の衝突回避
                dest_path = self._get_unique_destination_path(species_folder, source_path.name)
                
                # ファイルのコピーまたは移動
                try:
                    if copy_files:
                        shutil.copy2(source_path, dest_path)
                        self.logger.debug(f"コピー: {source_path.name} -> {folder_name}/")
                    else:
                        shutil.move(source_path, dest_path)
                        self.logger.debug(f"移動: {source_path.name} -> {folder_name}/")
                    
                    # 組織化マップに追加（日付ありモードは species/YYYY-MM-DD 単位で集計）
                    map_key = self._make_map_key(folder_name, species_folder)
                    organization_map.setdefault(map_key, []).append(str(dest_path))

                except Exception as e:
                    self.logger.error(f"ファイル{operation}エラー {source_path}: {str(e)}")

            self.logger.info(f"ファイル振り分け完了: {len(organization_map)} フォルダ作成")
            return organization_map

        except Exception as e:
            self.logger.error(f"ファイル振り分けエラー: {str(e)}")
            raise

    def organize_images_by_species_from_csv(
        self,
        csv_path: str,
        copy_files: bool = True,
        organize_by_date: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        progress_interval: int = 100,
    ) -> Dict[str, List[str]]:
        """CSVファイルから検出結果を読み込み、画像ファイルを種別フォルダに振り分け（ストリーミング版）

        Args:
            csv_path: 検出結果CSVのパス
            copy_files: True=コピー, False=移動
            organize_by_date: 日付→種別の階層で振り分け
            progress_callback: (processed, total, current_path) を受け取る進捗コールバック。
                1万枚コピー時の進捗表示などに使用。None なら呼ばれない。
            progress_interval: コールバック呼び出し間隔（枚数）。既定100枚毎。
        """
        organization_map: Dict[str, List[str]] = {}
        operation = "コピー" if copy_files else "移動"

        self.logger.info(f"ファイル{operation}による振り分けを開始（CSVベース）...")
        self.logger.info(f"ソースCSV: {csv_path}")
        if organize_by_date:
            self.logger.info("日付別サブフォルダを有効化")

        # 進捗表示用に総行数を1度数える（10K件で ~10ms）
        total_rows = 0
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f) - 1  # ヘッダー除く
                total_rows = max(0, total_rows)
        except OSError:
            total_rows = 0

        try:
            processed = 0
            # CSVを1行ずつ読み込んで処理（メモリ効率化）
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    image_path = row.get('image_path', '')
                    source_path = Path(image_path)

                    if not source_path.exists():
                        self.logger.warning(f"ソースファイルが存在しません: {source_path}")
                        processed += 1
                        continue

                    species_name = row.get('species', '') or ''
                    common_name = row.get('common_name', '') or ''
                    cached_date = (row.get('image_date') or '').strip() or None

                    if (not species_name
                            or (SpeciesDetectorDirect.is_no_detection_label(species_name)
                                and SpeciesDetectorDirect.is_no_detection_label(common_name))):
                        folder_name = NO_DETECTION_FOLDER
                    else:
                        folder_name = self._create_safe_folder_name(species_name, common_name)

                    # 出力フォルダの決定（日付サブフォルダ対応、CSV内日付を優先利用）
                    species_folder = self._resolve_target_folder(
                        folder_name, source_path, organize_by_date, cached_date=cached_date
                    )
                    species_folder.mkdir(parents=True, exist_ok=True)

                    dest_path = self._get_unique_destination_path(species_folder, source_path.name)

                    try:
                        if copy_files:
                            shutil.copy2(source_path, dest_path)
                        else:
                            shutil.move(source_path, dest_path)

                        map_key = self._make_map_key(folder_name, species_folder)
                        organization_map.setdefault(map_key, []).append(str(dest_path))

                    except OSError as e:
                        self.logger.error(f"ファイル{operation}エラー {source_path}: {e}")

                    processed += 1
                    if progress_callback and (processed % progress_interval == 0 or processed == total_rows):
                        try:
                            progress_callback(processed, total_rows, str(source_path))
                        except Exception:
                            self.logger.exception("振り分け進捗コールバック例外（処理は継続）")

            self.logger.info(f"ファイル振り分け完了: {len(organization_map)} フォルダ作成")
            return organization_map

        except OSError as e:
            self.logger.error(f"ファイル振り分けエラー: {e}")
            raise

    def _resolve_target_folder(self, folder_name: str, source_path: Path,
                               organize_by_date: bool,
                               cached_date: Optional[str] = None) -> Path:
        """振り分け先フォルダを決定。

        organize_by_date=True の場合、{YYYY-MM-DD}/{species}/ の日付優先構造を返す。
        cached_date が与えられれば EXIF 再読込をスキップ (検出CSVの image_date 列を利用)。
        日付が取得できない画像は 'unknown-date' フォルダ配下に配置。
        """
        if not organize_by_date:
            target = self.base_output_dir / folder_name
            return self._ensure_reasonable_path(target, folder_name)

        date_str = (cached_date or '').strip() or (extract_image_date(source_path) or 'unknown-date')
        target = self.base_output_dir / date_str / folder_name
        return self._ensure_reasonable_path(target, folder_name)

    def _ensure_reasonable_path(self, target: Path, folder_name: str) -> Path:
        """振り分け先が Windows MAX_PATH に収まるか確認。超過しそうなら folder_name をハッシュ短縮。

        ファイル名を含む完全パスの長さは呼び出し元が別途チェックするのが理想だが、
        ここではフォルダ長の余裕を先行確保する。
        """
        str_path = str(target)
        if len(str_path) < _MAX_PATH_WARN_THRESHOLD:
            return target

        # 短縮: 元 folder_name を 40 字に切り詰め + SHA1 の先頭8桁を付与して一意性確保
        digest = hashlib.sha1(folder_name.encode('utf-8')).hexdigest()[:8]
        shortened = f"{folder_name[:40]}_{digest}"
        # 先頭のフォルダ部分 (例: 日付/) は維持したいので末尾 segment だけ差し替え
        new_target = target.parent / shortened
        self.logger.warning(
            "振り分け先パスが長すぎるためフォルダ名を短縮: %s -> %s",
            folder_name, shortened,
        )
        return new_target

    def _make_map_key(self, folder_name: str, target_folder: Path) -> str:
        """organization_map のキー。日付サブフォルダ時は 'YYYY-MM-DD/species' を返す"""
        rel = target_folder.relative_to(self.base_output_dir)
        rel_str = str(rel).replace(os.sep, '/')
        return rel_str if rel_str != folder_name else folder_name

    def _create_safe_folder_name(self, species_name: str, common_name: str) -> str:
        """安全なフォルダ名を作成"""
        # 無効な文字を置換
        invalid_chars = '<>:"/\\|?*'
        
        # メインの名前を決定
        if common_name and common_name != species_name:
            main_name = f"{common_name}_{species_name}"
        else:
            main_name = species_name
        
        # 無効な文字を置換
        safe_name = main_name
        for char in invalid_chars:
            safe_name = safe_name.replace(char, '_')
        
        # 長すぎる場合は切り詰め
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        # 空の場合のフォールバック
        if not safe_name.strip():
            safe_name = "Unknown_Species"
        
        return safe_name
    
    def _get_unique_destination_path(self, folder: Path, filename: str) -> Path:
        """ファイル名の衝突を回避してユニークなパスを取得"""
        base_path = folder / filename
        
        if not base_path.exists():
            return base_path
        
        # ファイル名と拡張子を分離
        stem = base_path.stem
        suffix = base_path.suffix
        
        # 番号を付けて重複を回避
        counter = 1
        while True:
            new_filename = f"{stem}_{counter:03d}{suffix}"
            new_path = folder / new_filename
            
            if not new_path.exists():
                return new_path
            
            counter += 1
            
            # 無限ループ防止
            if counter > 9999:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                new_filename = f"{stem}_{timestamp}{suffix}"
                return folder / new_filename
    
    def create_species_summary_file(self, organization_map: Dict[str, List[str]]) -> str:
        """種別振り分けサマリーファイルを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"file_organization_summary_{timestamp}.json"
        summary_path = self.base_output_dir / summary_filename
        
        try:
            # サマリー情報の作成
            summary_data = {
                "created_at": datetime.now().isoformat(),
                "total_folders": len(organization_map),
                "total_files": sum(len(files) for files in organization_map.values()),
                "folders": {}
            }
            
            for folder_name, file_paths in organization_map.items():
                summary_data["folders"][folder_name] = {
                    "file_count": len(file_paths),
                    "files": [os.path.basename(path) for path in file_paths]
                }
            
            # JSONファイルに保存
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"振り分けサマリーファイル作成: {summary_path}")
            return str(summary_path)
            
        except Exception as e:
            self.logger.error(f"サマリーファイル作成エラー: {str(e)}")
            raise
    
    def create_folder_readme(self, folder_path: Path, species_info: Dict[str, Any]):
        """各フォルダにREADMEファイルを作成"""
        readme_path = folder_path / "README.txt"
        
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("Wildlife Detector - 検出結果フォルダ\n")
                f.write("=" * 40 + "\n\n")
                f.write(f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"フォルダ名: {folder_path.name}\n\n")

                if species_info:
                    f.write("検出情報:\n")
                    f.write(f"  種名: {species_info.get('species', 'N/A')}\n")
                    f.write(f"  一般名: {species_info.get('common_name', 'N/A')}\n")
                    f.write(f"  学名: {species_info.get('scientific_name', 'N/A')}\n")
                    f.write(f"  カテゴリ: {species_info.get('category', 'N/A')}\n")
                    f.write(f"  平均信頼度: {species_info.get('avg_confidence', 0):.3f}\n\n")

                f.write("このフォルダには、Wildlife Detectorによって\n")
                f.write("同一種として検出された画像ファイルが格納されています。\n\n")
                f.write("注意: 検出精度は100%ではありません。\n")
                f.write("必要に応じて手動での確認・修正を行ってください。\n")
            
            self.logger.debug(f"READMEファイル作成: {readme_path}")
            
        except Exception as e:
            self.logger.warning(f"READMEファイル作成エラー {readme_path}: {str(e)}")
    
    def cleanup_empty_folders(self):
        """空のフォルダを削除"""
        try:
            removed_count = 0
            
            for folder_path in self.base_output_dir.rglob('*'):
                if folder_path.is_dir() and not any(folder_path.iterdir()):
                    try:
                        folder_path.rmdir()
                        removed_count += 1
                        self.logger.debug(f"空フォルダを削除: {folder_path}")
                    except OSError:
                        pass  # 削除できない場合は無視
            
            if removed_count > 0:
                self.logger.info(f"空フォルダを {removed_count} 個削除しました")
                
        except Exception as e:
            self.logger.warning(f"空フォルダ削除エラー: {str(e)}")
    
    def get_organization_stats(self, organization_map: Dict[str, List[str]]) -> Dict[str, Any]:
        """振り分け統計情報を取得"""
        total_files = sum(len(files) for files in organization_map.values())
        
        stats = {
            "total_folders": len(organization_map),
            "total_files": total_files,
            "average_files_per_folder": total_files / len(organization_map) if organization_map else 0,
            "largest_folder": max(organization_map.items(), key=lambda x: len(x[1])) if organization_map else None,
            "folder_distribution": {
                folder: len(files) for folder, files in organization_map.items()
            }
        }
        
        return stats
