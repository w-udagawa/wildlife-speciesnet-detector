"""
テーマ / スタイルシート定義モジュール

Wildlife Detector のフィールドグリーン基調デザイン（claude.ai/design 由来）を
アプリ全体に適用するための Qt スタイルシート（QSS）を提供します。

深緑 #2E6B4F を基調に、紙のような温かいニュートラル背景でまとめ、
派手さより信頼感・可読性を優先しています。ダークモードは次段階（設定の
テーマ選択は現状ハイライトのみ）。
"""

# デザイントークン（gui/widgets.py の COL と一致させること）
_GREEN = "#2E6B4F"
_GREEN_DARK = "#245641"
_PAPER = "#F6F5F1"
_PANEL = "#FBFAF8"
_BORDER = "#E4E2DA"
_INK = "#1C1B18"
_MUTED = "#52514E"
_FAINT = "#898781"
_TINT = "#F0F6F2"
_HOVER = "#EFEEE8"
_BAR_TRACK = "#DCEAE1"
_DANGER = "#D03B3B"
_DANGER_BD = "#EBC5C5"
_DANGER_BG = "#FBEDED"

FIELD_GREEN_QSS = f"""
* {{
    font-family: "Segoe UI", "Yu Gothic UI", "Hiragino Sans", "Noto Sans JP", sans-serif;
    font-size: 13px;
    color: {_INK};
}}
QWidget#Root {{ background: {_PAPER}; }}
QMainWindow, QDialog, QMessageBox {{ background: {_PAPER}; }}
QLabel {{ background: transparent; color: {_INK}; }}

QFrame#Sidebar {{ background: {_PANEL}; border-right: 1px solid {_BORDER}; }}

QFrame#Card {{
    background: #FFFFFF;
    border: 1px solid {_BORDER};
    border-radius: 12px;
}}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* --- ドロップ領域 --- */
QFrame#DropArea {{
    border: 1.5px dashed #BFCFC4;
    background: {_TINT};
    border-radius: 12px;
}}
QFrame#DropArea[hover="true"] {{ border: 1.5px dashed {_GREEN}; }}

/* --- ボタン（セカンダリ） --- */
QPushButton {{
    background: #FFFFFF;
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {_INK};
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {_TINT}; }}
QPushButton:disabled {{ color: {_FAINT}; background: #FFFFFF; border-color: {_BORDER}; }}

QPushButton#Primary {{
    background: {_GREEN};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 12px 26px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton#Primary[compact="true"] {{ padding: 9px 16px; font-size: 13px; border-radius: 8px; }}
QPushButton#Primary:hover {{ background: {_GREEN_DARK}; }}
QPushButton#Primary:disabled {{ background: #A9C4B6; color: #EAF2ED; }}

QPushButton#Danger {{
    background: #FFFFFF;
    border: 1px solid {_DANGER_BD};
    color: {_DANGER};
    border-radius: 8px;
    padding: 9px 16px;
}}
QPushButton#Danger:hover {{ background: {_DANGER_BG}; }}
QPushButton#Danger:disabled {{ color: #C9A3A3; border-color: #EEDCDC; }}

QPushButton#Ghost {{
    background: transparent;
    border: none;
    color: {_GREEN_DARK};
    padding: 9px 16px;
}}
QPushButton#Ghost:hover {{ background: {_TINT}; }}

QPushButton#ThemeBtn {{
    background: #FFFFFF;
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    color: {_MUTED};
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#ThemeBtn:checked {{
    border: 2px solid {_GREEN};
    color: {_GREEN_DARK};
    background: {_TINT};
    font-weight: 600;
}}

/* --- 入力系 --- */
QLineEdit, QComboBox, QSpinBox {{
    background: {_PAPER};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {_INK};
    font-size: 13px;
    font-weight: 400;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {_GREEN}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid {_BORDER};
    outline: none;
    selection-background-color: {_TINT};
    selection-color: {_INK};
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 16px; }}

/* --- プログレスバー --- */
QProgressBar#Hero {{
    border: none;
    background: {_BAR_TRACK};
    border-radius: 5px;
}}
QProgressBar#Hero::chunk {{ background: {_GREEN}; border-radius: 5px; }}

/* --- スライダー --- */
QSlider::groove:horizontal {{ height: 4px; background: {_BAR_TRACK}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {_GREEN}; border-radius: 2px; }}
QSlider::add-page:horizontal {{ background: {_BAR_TRACK}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {_GREEN};
    width: 14px; height: 14px;
    margin: -6px 0;
    border-radius: 9px;
}}

/* --- テーブル --- */
QTableWidget {{
    background: #FFFFFF;
    border: none;
    gridline-color: {_BORDER};
    outline: none;
}}
QTableWidget#FileTable {{ background: transparent; }}
QHeaderView::section {{
    background: #FFFFFF;
    color: {_MUTED};
    border: none;
    border-bottom: 1px solid {_BORDER};
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    text-align: left;
}}
QTableWidget::item {{
    border-bottom: 1px solid {_BORDER};
    padding: 6px 10px;
    color: {_INK};
}}
QTableWidget::item:selected {{ background: {_TINT}; color: {_INK}; }}

/* --- テキストエリア（ログ） --- */
QTextEdit#Log {{
    background: {_PAPER};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: {_MUTED};
}}

/* --- スクロールバー --- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #D3D1C9; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #BEBCB3; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #D3D1C9; border-radius: 5px; min-width: 30px; }}

/* --- ツールチップ --- */
QToolTip {{
    background: {_INK}; color: #FFFFFF; border: none;
    padding: 4px 8px; border-radius: 4px;
}}
"""


def apply_app_style(app) -> None:
    """QApplication にフィールドグリーンのスタイルを適用する。"""
    app.setStyleSheet(FIELD_GREEN_QSS)
