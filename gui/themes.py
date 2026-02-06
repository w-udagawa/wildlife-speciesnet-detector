"""
テーマ設定モジュール
Wildlife Detector用のカスタムテーマ管理
"""
from typing import Dict, Any
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

class ThemeManager:
    """テーマ管理クラス"""
    
    def __init__(self):
        self.current_theme = "modern_blue"
        self.themes = self.load_themes()
    
    def load_themes(self) -> Dict[str, Dict[str, Any]]:
        """テーマ定義を読み込み"""
        return {
            "modern_blue": {
                "name": "モダンブルー",
                "primary_color": "#2196F3",
                "secondary_color": "#1976D2",
                "success_color": "#4CAF50",
                "warning_color": "#FF9800",
                "error_color": "#f44336",
                "background_color": "#f5f5f5",
                "card_background": "#ffffff",
                "text_color": "#333333",
                "style": self.get_modern_blue_style()
            },
            "dark_theme": {
                "name": "ダークテーマ",
                "primary_color": "#1565C0",
                "secondary_color": "#0D47A1",
                "success_color": "#388E3C",
                "warning_color": "#F57C00",
                "error_color": "#D32F2F",
                "background_color": "#121212",
                "card_background": "#1e1e1e",
                "text_color": "#ffffff",
                "style": self.get_dark_theme_style()
            },
            "nature_green": {
                "name": "ナチュラルグリーン",
                "primary_color": "#4CAF50",
                "secondary_color": "#388E3C",
                "success_color": "#8BC34A",
                "warning_color": "#FF9800",
                "error_color": "#f44336",
                "background_color": "#f1f8e9",
                "card_background": "#ffffff",
                "text_color": "#1B5E20",
                "style": self.get_nature_green_style()
            }
        }
    
    def get_modern_blue_style(self) -> str:
        """モダンブルーテーマのスタイル"""
        return """
            QMainWindow {
                background: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #e0e0e0;
                color: #333;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: white;
                color: #2196F3;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background: #f0f0f0;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #333;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background: white;
            }
        """
    
    def get_dark_theme_style(self) -> str:
        """ダークテーマのスタイル"""
        return """
            QMainWindow {
                background: #121212;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #333333;
                background: #1e1e1e;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #333333;
                color: #ffffff;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                color: #1565C0;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background: #2a2a2a;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #ffffff;
                border: 2px solid #333333;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
        """
    
    def get_nature_green_style(self) -> str:
        """ナチュラルグリーンテーマのスタイル"""
        return """
            QMainWindow {
                background: #f1f8e9;
            }
            QTabWidget::pane {
                border: 1px solid #8BC34A;
                background: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #C8E6C9;
                color: #1B5E20;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: white;
                color: #4CAF50;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                background: #E8F5E8;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #1B5E20;
                border: 2px solid #8BC34A;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background: white;
            }
            QLabel {
                color: #1B5E20;
            }
        """
    
    def apply_theme(self, theme_name: str, app: QApplication):
        """テーマを適用"""
        if theme_name in self.themes:
            theme = self.themes[theme_name]
            app.setStyleSheet(theme["style"])
            self.current_theme = theme_name
            return True
        return False
    
    def get_current_theme(self) -> Dict[str, Any]:
        """現在のテーマを取得"""
        return self.themes.get(self.current_theme, self.themes["modern_blue"])
    
    def get_theme_list(self) -> list:
        """利用可能なテーマ一覧を取得"""
        return [(key, value["name"]) for key, value in self.themes.items()]

# グローバルテーママネージャー
theme_manager = ThemeManager()
