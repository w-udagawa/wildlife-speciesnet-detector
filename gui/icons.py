"""
アイコンリソース管理モジュール
Wildlife Detector用のアイコンとリソース管理
"""
import os
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QStyle, QApplication

class IconManager:
    """アイコン管理クラス"""
    
    def __init__(self):
        self.app = QApplication.instance()
        self.style = self.app.style() if self.app else None
        
    def get_system_icon(self, icon_type: str) -> QIcon:
        """システムアイコンを取得"""
        if not self.style:
            return QIcon()
            
        icon_map = {
            'folder': QStyle.SP_DirIcon,
            'file': QStyle.SP_FileIcon,
            'computer': QStyle.SP_ComputerIcon,
            'save': QStyle.SP_DialogSaveButton,
            'open': QStyle.SP_DialogOpenButton,
            'apply': QStyle.SP_DialogApplyButton,
            'cancel': QStyle.SP_DialogCancelButton,
            'help': QStyle.SP_DialogHelpButton,
            'info': QStyle.SP_MessageBoxInformation,
            'warning': QStyle.SP_MessageBoxWarning,
            'error': QStyle.SP_MessageBoxCritical,
            'question': QStyle.SP_MessageBoxQuestion,
        }
        
        standard_pixmap = icon_map.get(icon_type, QStyle.SP_ComputerIcon)
        return self.style.standardIcon(standard_pixmap)
    
    def create_text_icon(self, text: str, color: str = "#2196F3") -> QIcon:
        """テキストからアイコンを作成"""
        pixmap = QPixmap(32, 32)
        pixmap.fill()
        
        from PySide6.QtGui import QPainter, QFont, QColor
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        font = QFont("Segoe UI", 16, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        
        painter.drawText(pixmap.rect(), text, alignment=4)  # AlignCenter
        painter.end()
        
        return QIcon(pixmap)

# グローバルアイコンマネージャー
icon_manager = IconManager()
