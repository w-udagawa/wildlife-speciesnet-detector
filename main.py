"""
Wildlife Detector - メインエントリーポイント
野生生物検出デスクトップアプリケーション

Google SpeciesNetを使用した高精度な鳥類・哺乳類検出
"""

import sys
import os
import logging
from pathlib import Path

# アプリケーションのルートディレクトリをパスに追加
app_root = Path(__file__).parent  # プロジェクトルートディレクトリ
sys.path.insert(0, str(app_root))

try:
    from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap, QFont
except ImportError:
    print("エラー: PySide6がインストールされていません")
    print("次のコマンドでインストールしてください:")
    print("pip install PySide6")
    sys.exit(1)

from gui.main_window import MainWindow

class WildlifeDetectorApp:
    """Wildlife Detector アプリケーションクラス"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定"""
        log_dir = Path.home() / "WildlifeDetector" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / "wildlife_detector.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Wildlife Detector アプリケーション開始")
    
    def check_dependencies(self) -> bool:
        """依存関係チェック"""
        missing_packages = []
        
        # 必須パッケージのチェック
        required_packages = {
            'numpy': 'numpy',
            'pandas': 'pandas', 
            'PIL': 'Pillow',
            'cv2': 'opencv-python'
        }
        
        for module, package in required_packages.items():
            try:
                __import__(module)
                self.logger.info(f"✓ {package} - OK")
            except ImportError:
                missing_packages.append(package)
                self.logger.error(f"✗ {package} - 未インストール")
        
        # SpeciesNetの特別チェック
        try:
            import speciesnet
            self.logger.info("✓ speciesnet - OK")
        except ImportError:
            missing_packages.append('speciesnet')
            self.logger.error("✗ speciesnet - 未インストール")
        
        if missing_packages:
            self.show_dependency_error(missing_packages)
            return False
        
        return True
    
    def show_dependency_error(self, missing_packages: list):
        """依存関係エラーの表示"""
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        error_msg = "以下のパッケージがインストールされていません:\\n\\n"
        error_msg += "\\n".join([f"• {pkg}" for pkg in missing_packages])
        error_msg += "\\n\\n次のコマンドでインストールしてください:\\n"
        error_msg += "pip install " + " ".join(missing_packages)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Wildlife Detector - 依存関係エラー")
        msg_box.setText("必要なパッケージがインストールされていません")
        msg_box.setDetailedText(error_msg)
        msg_box.exec()
    
    def create_splash_screen(self) -> QSplashScreen:
        """スプラッシュスクリーンの作成"""
        # 簡単なスプラッシュスクリーンを作成
        # 実際のアプリケーションでは画像ファイルを使用
        splash_pix = QPixmap(400, 300)
        splash_pix.fill(Qt.darkBlue)
        
        splash = QSplashScreen(splash_pix)
        splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        
        # フォント設定
        font = QFont("Arial", 14, QFont.Bold)
        splash.setFont(font)
        
        splash.showMessage(
            "Wildlife Detector\\n\\n"
            "野生生物検出アプリケーション\\n"
            "Powered by Google SpeciesNet\\n\\n"
            "初期化中...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        
        return splash
    
    def initialize_application(self):
        """アプリケーション初期化"""
        # QApplicationの作成
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Wildlife Detector")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("Wildlife Detection Team")
        
        # アプリケーションの詳細設定
        self.app.setQuitOnLastWindowClosed(True)
        
        # スプラッシュスクリーンの表示
        splash = self.create_splash_screen()
        splash.show()
        self.app.processEvents()
        
        # メインウィンドウの作成
        splash.showMessage(
            "Wildlife Detector\\n\\n"
            "野生生物検出アプリケーション\\n"
            "Powered by Google SpeciesNet\\n\\n"
            "UIを初期化中...",
            Qt.AlignCenter | Qt.AlignBottom,
            Qt.white
        )
        self.app.processEvents()
        
        try:
            self.main_window = MainWindow()
            
            # スプラッシュスクリーンを少し表示してから閉じる
            splash.showMessage(
                "Wildlife Detector\\n\\n"
                "野生生物検出アプリケーション\\n"
                "Powered by Google SpeciesNet\\n\\n"
                "準備完了!",
                Qt.AlignCenter | Qt.AlignBottom,
                Qt.white
            )
            self.app.processEvents()
            
            # 2秒間表示
            import time
            time.sleep(2)
            
            splash.close()
            
            # メインウィンドウの表示
            self.main_window.show()
            
            self.logger.info("アプリケーション初期化完了")
            
        except Exception as e:
            splash.close()
            self.logger.error(f"アプリケーション初期化エラー: {str(e)}")
            self.show_initialization_error(str(e))
            return False
        
        return True
    
    def show_initialization_error(self, error_message: str):
        """初期化エラーの表示"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Wildlife Detector - 初期化エラー")
        msg_box.setText("アプリケーションの初期化に失敗しました")
        msg_box.setDetailedText(f"エラー詳細:\\n{error_message}")
        msg_box.exec()
    
    def run(self) -> int:
        """アプリケーション実行"""
        try:
            # 依存関係チェック
            if not self.check_dependencies():
                return 1
            
            # アプリケーション初期化
            if not self.initialize_application():
                return 1
            
            # イベントループ開始
            self.logger.info("アプリケーション実行開始")
            exit_code = self.app.exec()
            self.logger.info(f"アプリケーション終了 (終了コード: {exit_code})")
            
            return exit_code
            
        except KeyboardInterrupt:
            self.logger.info("ユーザーによる中断")
            return 0
        except Exception as e:
            self.logger.error(f"予期しないエラー: {str(e)}")
            return 1
        finally:
            # クリーンアップ
            if self.main_window:
                self.main_window.close()

def main():
    """メイン関数"""
    print("=" * 60)
    print("Wildlife Detector - 野生生物検出アプリケーション")
    print("Powered by Google SpeciesNet")
    print("=" * 60)
    
    # アプリケーション実行
    app = WildlifeDetectorApp()
    exit_code = app.run()
    
    print("\\nWildlife Detector を終了しました")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
