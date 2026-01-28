"""
Wildlife Detector ファイル管理モジュール
検出結果に基づくファイル振り分け機能
"""
import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

from core.species_detector import DetectionResult

class FileManager:
    """ファイル管理クラス"""
    
    def __init__(self, base_output_dir: str):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def organize_images_by_species(self, results: List[DetectionResult], 
                                 copy_files: bool = True) -> Dict[str, List[str]]:
        """検出結果に基づいて画像ファイルを種別フォルダに振り分け"""
        organization_map = {}
        operation = "コピー" if copy_files else "移動"
        
        self.logger.info(f"ファイル{operation}による振り分けを開始...")
        
        try:
            for result in results:
                source_path = Path(result.image_path)
                
                if not source_path.exists():
                    self.logger.warning(f"ソースファイルが存在しません: {source_path}")
                    continue
                
                if result.has_detections():
                    # 検出された場合、最も信頼度の高い種で分類
                    best_detection = result.get_best_detection()
                    species_name = best_detection.get('species', 'Unknown')
                    common_name = best_detection.get('common_name', '')
                    confidence = best_detection.get('confidence', 0)
                    
                    # フォルダ名の作成（安全な文字のみ使用）
                    folder_name = self._create_safe_folder_name(species_name, common_name)
                    
                else:
                    # 検出されなかった場合
                    folder_name = "未検出_No_Detection"
                
                # 出力フォルダの作成
                species_folder = self.base_output_dir / folder_name
                species_folder.mkdir(parents=True, exist_ok=True)
                
                # ファイル名の衝突回避
                dest_path = self._get_unique_destination_path(species_folder, source_path.name)
                
                # ファイルのコピーまたは移動
                try:
                    if copy_files:
                        shutil.copy2(source_path, dest_path)
                        self.logger.debug(f"コピー: {source_path.name} -> {folder_name}/")
                    else:
                        shutil.move(str(source_path), str(dest_path))
                        self.logger.debug(f"移動: {source_path.name} -> {folder_name}/")
                    
                    # 組織化マップに追加
                    if folder_name not in organization_map:
                        organization_map[folder_name] = []
                    organization_map[folder_name].append(str(dest_path))
                    
                except Exception as e:
                    self.logger.error(f"ファイル{operation}エラー {source_path}: {str(e)}")
            
            self.logger.info(f"ファイル振り分け完了: {len(organization_map)} フォルダ作成")
            return organization_map
            
        except Exception as e:
            self.logger.error(f"ファイル振り分けエラー: {str(e)}")
            raise
    
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
                f.write("Wildlife Detector - 検出結果フォルダ\\n")
                f.write("=" * 40 + "\\n\\n")
                f.write(f"作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"フォルダ名: {folder_path.name}\\n\\n")
                
                if species_info:
                    f.write("検出情報:\\n")
                    f.write(f"  種名: {species_info.get('species', 'N/A')}\\n")
                    f.write(f"  一般名: {species_info.get('common_name', 'N/A')}\\n")
                    f.write(f"  学名: {species_info.get('scientific_name', 'N/A')}\\n")
                    f.write(f"  カテゴリ: {species_info.get('category', 'N/A')}\\n")
                    f.write(f"  平均信頼度: {species_info.get('avg_confidence', 0):.3f}\\n\\n")
                
                f.write("このフォルダには、Wildlife Detectorによって\\n")
                f.write("同一種として検出された画像ファイルが格納されています。\\n\\n")
                f.write("注意: 検出精度は100%ではありません。\\n")
                f.write("必要に応じて手動での確認・修正を行ってください。\\n")
            
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
