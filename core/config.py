"""
Wildlife Detector 設定管理モジュール

アプリケーションの設定を管理します。
設定はJSONファイルとして保存され、起動時に自動的にロードされます。

主要クラス:
    - AppConfig: アプリケーション設定のデータクラス
    - ConfigManager: 設定の保存/読み込みを管理

設定項目:
    - 検出設定（信頼度閾値、バッチサイズ、地域フィルター）
    - パフォーマンス設定（ワーカー数、GPU使用）
    - メモリ管理設定（GC間隔、中間保存間隔）
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, fields

@dataclass
class AppConfig:
    """アプリケーション設定クラス"""

    # 検出設定
    confidence_threshold: float = 0.1
    batch_size: int = 32
    country_filter: str = "JPN"
    max_workers: int = 2  # WSL2環境向けに2に削減（旧: 4）
    use_gpu: bool = False

    # 出力設定
    create_species_folders: bool = True
    copy_images_to_folders: bool = True
    output_csv: bool = True

    # UI設定
    window_size: tuple = (1200, 800)
    theme: str = "default"

    # 高度な設定
    max_image_size: tuple = (1920, 1080)
    processing_timeout: int = 300  # 5分

    # 大量画像処理向けメモリ管理設定
    intermediate_save_interval: int = 100  # 中間保存間隔（枚数）
    gc_interval: int = 50  # ガベージコレクション間隔（枚数）
    consecutive_error_limit: int = 3  # 連続エラー上限（この回数超えると処理中断）
    run_mode: str = "multi_thread"  # SpeciesNet APIの実行モード（"multi_thread" or "single"）
    
    @classmethod
    def get_default(cls) -> 'AppConfig':
        """デフォルト設定を取得"""
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """辞書から設定を作成（未知のキーは無視）"""
        valid_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.home() / "WildlifeDetector"
        
        self.config_dir = config_dir
        self.config_file = self.config_dir / "config.json"
        self.logger = logging.getLogger(__name__)
        
        # 設定ディレクトリの作成
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> AppConfig:
        """設定をロード"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = AppConfig.from_dict(data)
                    self.logger.info(f"設定ファイルをロードしました: {self.config_file}")
                    return config
            else:
                self.logger.info("設定ファイルが存在しません。デフォルト設定を使用します")
                return AppConfig.get_default()
                
        except Exception as e:
            self.logger.error(f"設定ロードエラー: {str(e)}")
            self.logger.info("デフォルト設定を使用します")
            return AppConfig.get_default()
    
    def save_config(self, config: AppConfig) -> bool:
        """設定を保存"""
        try:
            if config is None:
                self.logger.error("設定保存エラー: 保存する設定が指定されていません")
                return False
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"設定ファイルを保存しました: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定保存エラー: {str(e)}")
            return False
    
    def reset_config(self) -> AppConfig:
        """設定をリセット"""
        config = AppConfig.get_default()
        self.save_config(config)
        self.logger.info("設定をデフォルトにリセットしました")
        return config
    
    def backup_config(self) -> bool:
        """設定のバックアップ作成"""
        try:
            if self.config_file.exists():
                backup_file = self.config_dir / f"config_backup_{int(time.time())}.json"
                import shutil
                shutil.copy2(self.config_file, backup_file)
                self.logger.info(f"設定バックアップを作成しました: {backup_file}")
                return True
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {str(e)}")
            return False
