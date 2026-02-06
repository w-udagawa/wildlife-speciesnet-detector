"""
スプラッシュスクリーン
Wildlife Detector起動時の美しいローディング画面
"""
import sys
import time
from PySide6.QtWidgets import QApplication, QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QLinearGradient

class SplashScreen(QSplashScreen):
    """モダンなスプラッシュスクリーン"""
    
    def __init__(self):
        # スプラッシュ画像を作成
        pixmap = self.create_splash_pixmap()
        super().__init__(pixmap)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # プログレスバー設定
        self.progress = 0
        self.setup_ui()
        
        # タイマー設定
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)  # 100ms間隔
    
    def create_splash_pixmap(self) -> QPixmap:
        """スプラッシュ画像を作成"""
        pixmap = QPixmap(600, 400)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # グラデーション背景
        gradient = QLinearGradient(0, 0, 600, 400)
        gradient.setColorAt(0, QColor("#1976D2"))
        gradient.setColorAt(1, QColor("#42A5F5"))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 600, 400, 20, 20)
        
        # タイトル
        painter.setPen(QColor("white"))
        title_font = QFont("Segoe UI", 32, QFont.Bold)
        painter.setFont(title_font)
        painter.drawText(50, 150, "🦅 Wildlife Detector")
        
        # サブタイトル
        subtitle_font = QFont("Segoe UI", 16)
        painter.setFont(subtitle_font)
        painter.setPen(QColor(255, 255, 255, 180))
        painter.drawText(50, 190, "AI搭載野生生物検出システム")
        
        # バージョン
        version_font = QFont("Segoe UI", 12)
        painter.setFont(version_font)
        painter.drawText(50, 220, "Version 2.0 - SpeciesNet統合版")
        
        # フッター
        footer_font = QFont("Segoe UI", 10)
        painter.setFont(footer_font)
        painter.setPen(QColor(255, 255, 255, 150))
        painter.drawText(50, 350, "起動中...")
        
        painter.end()
        return pixmap
    
    def setup_ui(self):
        """UI設定"""
        self.setFixedSize(600, 400)
        
    def update_progress(self):
        """プログレス更新"""
        self.progress += 2
        
        if self.progress <= 100:
            # ローディングメッセージ
            messages = [
                "システム初期化中...",
                "SpeciesNet読み込み中...",
                "GUI設定中...",
                "設定ファイル読み込み中...",
                "準備完了"
            ]
            
            message_index = min(self.progress // 20, len(messages) - 1)
            message = messages[message_index]
            
            self.showMessage(f"{message} ({self.progress}%)", 
                           Qt.AlignBottom | Qt.AlignCenter, 
                           QColor("white"))
        else:
            self.timer.stop()
            self.close()
    
    def mousePressEvent(self, event):
        """マウスクリックで閉じる"""
        pass  # クリックでは閉じない

def show_splash():
    """スプラッシュスクリーンを表示"""
    splash = SplashScreen()
    splash.show()
    
    # プロセスイベントを処理
    QApplication.processEvents()
    
    return splash
