"""
Wildlife Detector メインGUIモジュール

PySide6ベースのメインウィンドウを提供します。
フィールドグリーン基調のデザイン（claude.ai/design 由来）に沿って、
左サイドバーの番号付きステッパー（① 画像の選択 → ② 検出処理 → ③ 結果）＋
別枠の「設定」でワークフローを表現します。

主要クラス:
    - ProcessingThread: バッチ処理用のワーカースレッド
    - MainWindow: アプリケーションのメインウィンドウ

機能:
    - 画像ファイル/フォルダの選択（ドラッグ＆ドロップ対応）
    - バッチ処理の実行と進捗表示（ヒーロー進捗率・統計タイル・ログ）
    - 結果のサマリータイル / トップ5種の横棒グラフ / 詳細テーブル
      （和名優先・信頼度メーター・カテゴリチップ・検索/カテゴリ絞り込み・ページング）
    - CSV出力とファイル振り分け・設定（信頼度スライダー・テーマ選択）
"""
import os
import csv
import shutil
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QGridLayout, QPushButton, QLabel,
                              QFileDialog, QTextEdit, QProgressBar, QStackedWidget,
                              QTableWidget, QTableWidgetItem, QLineEdit,
                              QCheckBox, QSpinBox, QComboBox, QMessageBox,
                              QFrame, QSlider, QHeaderView, QAbstractItemView,
                              QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QDesktopServices

from core.config import ConfigManager, AppConfig
from core.batch_processor import BatchProcessor, ProcessingStats
from core.species_detector_direct import DetectionResult
from utils.csv_exporter import CSVExporter
from utils.file_manager import FileManager

from gui.themes import FIELD_GREEN_QSS
from gui.widgets import (
    COL, ToggleSwitch, StatCard, StepperItem, NavItem, Bar, ConfidenceMeter,
    category_chip, classify_category, card, section_title, DropArea,
)


class ProcessingThread(QThread):
    """バッチ処理用スレッド"""

    progress_updated = Signal(float, str, object)  # progress, current_file, stats
    processing_completed = Signal(dict)  # summary dict (not list)
    error_occurred = Signal(str, str)  # title, message

    def __init__(self, processor: BatchProcessor, image_paths: List[str], output_dir: str,
                 resume_from_csv: Optional[str] = None):
        super().__init__()
        self.processor = processor
        self.image_paths = image_paths
        self.output_dir = output_dir
        self.resume_from_csv = resume_from_csv
        self.summary = {}

    def run(self):
        """処理スレッドの実行"""
        try:
            self.processor.set_progress_callback(self._on_progress)
            self.processor.set_error_callback(self._on_error)

            self.summary = self.processor.process_images(
                self.image_paths, self.output_dir, resume_from_csv=self.resume_from_csv
            )

            self.processing_completed.emit(self.summary)

        except Exception as e:
            self.error_occurred.emit("処理エラー", str(e))

    def _on_progress(self, progress: float, current_file: str, stats: ProcessingStats):
        self.progress_updated.emit(progress, current_file, stats)

    def _on_error(self, file_path: str, error_message: str):
        self.error_occurred.emit(f"ファイル処理エラー: {os.path.basename(file_path)}", error_message)

    def stop_processing(self):
        if self.processor:
            self.processor.stop_processing()


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""

    RESULTS_PER_PAGE = 100

    # ステッパー: ビュー → ステップ番号（設定は 0 = ワークフロー外）
    STEP_INDEX = {"input": 1, "processing": 2, "results": 3, "settings": 0}
    STEP_NUM = {"input": 1, "processing": 2, "results": 3}
    VIEW_STACK = {"input": 0, "processing": 1, "results": 2, "settings": 3}

    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

        self.processor = BatchProcessor(self.config)
        self.processing_thread = None

        # 選択・出力
        self.selected_files: List[str] = []
        self.output_folder: Optional[str] = None
        self._total_to_process = 0

        # 結果CSV
        self.results_csv_path = None
        self.results_summary = {}

        # ページング/絞り込み
        self.current_page = 0
        self.total_results = 0
        self._results_total_rows = 0
        self._results_unique_species = 0
        self._top5: List[tuple] = []
        self._cat_breakdown = ""
        self.search_query = ""
        self.cat_filter = "all"

        # 表示状態
        self.current_view = "input"
        self.theme_value = self.config.theme if self.config.theme in ("light", "dark", "auto") else "light"

        self.init_ui()
        self.setup_connections()

        self.setWindowTitle("Wildlife Detector — 野生生物検出")
        self.resize(*self.config.window_size)
        self.setMinimumSize(980, 680)

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        QApplication.instance().setStyleSheet(FIELD_GREEN_QSS)

        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_input_screen())       # 0
        self.stack.addWidget(self._build_processing_screen())  # 1
        self.stack.addWidget(self._build_results_screen())     # 2
        self.stack.addWidget(self._build_settings_screen())    # 3
        root.addWidget(self.stack, 1)

        self.set_view("input")
        self.statusBar().showMessage("準備完了")
        self.statusBar().setStyleSheet(
            f"color:{COL['faint']}; background:{COL['panel']}; "
            f"border-top:1px solid {COL['border']};")

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(236)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 20, 14, 16)
        lay.setSpacing(4)

        # ロゴ
        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(8, 0, 8, 14)
        logo_row.setSpacing(10)
        mark = QLabel("🦅")
        mark.setFixedSize(34, 34)
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(
            f"background:{COL['green']}; border-radius:9px; font-size:17px;")
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        t1 = QLabel("Wildlife Detector")
        t1.setStyleSheet("font-weight:600; font-size:14px;")
        t2 = QLabel("v2.1 · SpeciesNet")
        t2.setStyleSheet(f"font-size:11px; color:{COL['faint']};")
        title_box.addWidget(t1)
        title_box.addWidget(t2)
        logo_row.addWidget(mark, 0)
        logo_row.addLayout(title_box, 1)
        lay.addLayout(logo_row)

        # ワークフロー
        wf = QLabel("ワークフロー")
        wf.setStyleSheet(f"font-size:11px; color:{COL['faint']}; padding:10px 10px 6px;")
        lay.addWidget(wf)

        self.step_items: Dict[str, StepperItem] = {}
        for key, num, label in (("input", "1", "画像の選択"),
                                ("processing", "2", "検出処理"),
                                ("results", "3", "結果")):
            item = StepperItem(num, label)
            item.clicked.connect(lambda k=key: self.set_view(k))
            self.step_items[key] = item
            lay.addWidget(item)

        other = QLabel("その他")
        other.setStyleSheet(f"font-size:11px; color:{COL['faint']}; padding:10px 10px 6px;")
        lay.addWidget(other)

        self.settings_nav = NavItem("⚙  設定")
        self.settings_nav.clicked.connect(lambda: self.set_view("settings"))
        lay.addWidget(self.settings_nav)

        lay.addStretch()

        # フッター（状態表示）
        footer = QFrame()
        footer.setStyleSheet(f"border-top:1px solid {COL['border']};")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(8, 12, 8, 0)
        fl.setSpacing(6)
        fl.addWidget(self._status_line(COL["ok"], "SpeciesNet v4.0.1a 読み込み済み"))
        self.gpu_footer_lbl = self._status_line(COL["ok"], "")
        self._refresh_gpu_footer()
        fl.addWidget(self.gpu_footer_lbl)
        lay.addWidget(footer)

        return side

    def _status_line(self, dot_color: str, text: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(7)
        dot = QLabel()
        dot.setObjectName("StatusDot")
        dot.setFixedSize(7, 7)
        dot.setStyleSheet(f"background:{dot_color}; border-radius:3px;")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size:11px; color:{COL['muted']};")
        w._lbl = lbl  # 後から更新できるよう参照を保持
        h.addWidget(dot, 0)
        h.addWidget(lbl, 1)
        return w

    def _refresh_gpu_footer(self):
        on = self.config.use_gpu
        txt = "GPU: NVIDIA RTX 4060 使用中" if on else "GPU: 未使用（CPUで実行）"
        self.gpu_footer_lbl._lbl.setText(txt)
        color = COL["ok"] if on else COL["faint"]
        self.gpu_footer_lbl.findChild(QLabel, "StatusDot").setStyleSheet(
            f"background:{color}; border-radius:3px;")

    def _screen_scaffold(self, title: str, subtitle: str):
        """ヘッダー付きのスクロール可能な画面枠を返す。(page_widget, content_layout)"""
        from PySide6.QtWidgets import QScrollArea
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        body = QWidget()
        content = QVBoxLayout(body)
        content.setContentsMargins(32, 26, 32, 32)
        content.setSpacing(16)
        scroll.setWidget(body)

        head = QVBoxLayout()
        head.setSpacing(3)
        h1 = QLabel(title)
        h1.setStyleSheet("font-size:20px; font-weight:600;")
        sub = QLabel(subtitle)
        sub.setStyleSheet(f"font-size:13px; color:{COL['muted']};")
        sub.setWordWrap(True)
        head.addWidget(h1)
        head.addWidget(sub)
        content.addLayout(head)
        return page, content

    # ---------------------------------------------------------- Screen 1
    def _build_input_screen(self) -> QWidget:
        page, content = self._screen_scaffold(
            "画像の選択", "処理したい画像ファイルまたはフォルダを選び、出力先を設定します。")

        # ドロップ領域
        self.drop_area = DropArea()
        dl = QVBoxLayout(self.drop_area)
        dl.setContentsMargins(20, 34, 20, 34)
        dl.setSpacing(4)
        dl.setAlignment(Qt.AlignCenter)
        icon = QLabel("🗂️")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:34px;")
        t = QLabel("ここに画像やフォルダをドラッグ＆ドロップ")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:15px; font-weight:600;")
        s = QLabel("JPG / PNG / BMP / TIFF に対応 · サブフォルダも自動で検索します")
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet(f"font-size:12px; color:{COL['muted']};")
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(10)
        self.select_files_btn = QPushButton("📄 ファイルを選択")
        self.select_folder_btn = QPushButton("📁 フォルダを選択")
        btn_row.addWidget(self.select_files_btn)
        btn_row.addWidget(self.select_folder_btn)
        dl.addWidget(icon)
        dl.addWidget(t)
        dl.addWidget(s)
        dl.addSpacing(10)
        dl.addLayout(btn_row)
        content.addWidget(self.drop_area)

        # 選択中の画像
        sel_card = card()
        head = QHBoxLayout()
        head.setSpacing(6)
        self.file_count_label = QLabel("選択中の画像 0枚")
        self.file_count_label.setStyleSheet("font-size:14px; font-weight:600;")
        self.file_path_label = QLabel("")
        self.file_path_label.setStyleSheet(f"font-size:12px; color:{COL['faint']};")
        head.addWidget(self.file_count_label, 0)
        head.addWidget(self.file_path_label, 1)
        sel_card.layout().addLayout(head)

        self.file_table = QTableWidget(0, 2)
        self.file_table.setObjectName("FileTable")
        self.file_table.horizontalHeader().setVisible(False)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setShowGrid(False)
        self.file_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setFocusPolicy(Qt.NoFocus)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.file_table.setMaximumHeight(230)
        self._render_empty_file_table()
        sel_card.layout().addWidget(self.file_table)
        content.addWidget(sel_card)

        # 出力設定
        out_card = card()
        out_card.layout().addWidget(section_title("出力設定"))

        of_row = self._settings_row(
            "出力フォルダ", "CSVと振り分け画像の保存先")
        self.output_folder_label = QLabel("未選択")
        self.output_folder_label.setObjectName("PathChip")
        self.output_folder_label.setStyleSheet(
            f"font-size:12px; color:{COL['muted']}; background:{COL['paper']};"
            f"border:1px solid {COL['border']}; border-radius:6px; padding:5px 10px;")
        self.select_output_btn = QPushButton("変更")
        of_ctrl = QHBoxLayout()
        of_ctrl.setSpacing(10)
        of_ctrl.addWidget(self.output_folder_label)
        of_ctrl.addWidget(self.select_output_btn)
        of_row.addLayout(of_ctrl)
        out_card.layout().addWidget(self._row_wrap(of_row, first=True))

        self.create_folders_cb = ToggleSwitch(self.config.create_species_folders)
        out_card.layout().addWidget(self._toggle_row(
            "種別フォルダを作成", "例: ハシブトガラス_Corvus_macrorhynchos/", self.create_folders_cb))

        self.copy_images_cb = ToggleSwitch(self.config.copy_images_to_folders)
        out_card.layout().addWidget(self._toggle_row(
            "画像をコピー", "オフの場合は移動します", self.copy_images_cb))

        self.organize_by_date_cb = ToggleSwitch(self.config.organize_by_date)
        out_card.layout().addWidget(self._toggle_row(
            "撮影日ごとにサブフォルダを作成", "EXIF撮影日を使用（種別フォルダ配下）",
            self.organize_by_date_cb))
        content.addWidget(out_card)

        # 開始行
        start_row = QHBoxLayout()
        start_row.addStretch()
        self.est_time_label = QLabel("推定処理時間: —")
        self.est_time_label.setStyleSheet(f"font-size:12px; color:{COL['faint']};")
        self.start_btn = QPushButton("検出処理を開始 →")
        self.start_btn.setObjectName("Primary")
        self.start_btn.setEnabled(False)
        start_row.addWidget(self.est_time_label)
        start_row.addSpacing(14)
        start_row.addWidget(self.start_btn)
        content.addLayout(start_row)

        content.addStretch()
        return page

    def _settings_row(self, title: str, desc: str) -> QHBoxLayout:
        """タイトル＋説明（左）とコントロール（右）を並べる行レイアウトを返す。"""
        row = QHBoxLayout()
        row.setSpacing(16)
        text = QVBoxLayout()
        text.setSpacing(1)
        t = QLabel(title)
        t.setStyleSheet("font-size:13px;")
        d = QLabel(desc)
        d.setStyleSheet(f"font-size:12px; color:{COL['faint']};")
        text.addWidget(t)
        text.addWidget(d)
        row.addLayout(text, 1)
        return row

    def _row_wrap(self, row: QHBoxLayout, first: bool = False) -> QWidget:
        w = QWidget()
        w.setLayout(row)
        row.setContentsMargins(2, 11, 2, 11)
        if not first:
            w.setStyleSheet(f"QWidget {{ border-top:1px solid {COL['border']}; }}")
        return w

    def _toggle_row(self, title: str, desc: str, toggle: ToggleSwitch,
                    first: bool = False) -> QWidget:
        row = self._settings_row(title, desc)
        row.addWidget(toggle, 0, Qt.AlignVCenter)
        return self._row_wrap(row, first=first)

    def _render_empty_file_table(self):
        self.file_table.setRowCount(1)
        item = QTableWidgetItem("選択されたファイルがここに表示されます")
        item.setForeground(Qt.gray)
        self.file_table.setItem(0, 0, item)
        self.file_table.setItem(0, 1, QTableWidgetItem(""))

    # ---------------------------------------------------------- Screen 2
    def _build_processing_screen(self) -> QWidget:
        page, content = self._screen_scaffold(
            "検出処理",
            "SpeciesNet による解析を実行中です。処理はチャンク単位で自動保存され、"
            "中断してもレジュームできます。")

        # ヒーローカード
        hero = card()
        top = QHBoxLayout()
        top.setSpacing(12)
        self.progress_hero = QLabel("0%")
        self.progress_hero.setStyleSheet(
            f"font-size:48px; font-weight:600; color:{COL['green']};")
        self.processed_total_lbl = QLabel("0 / 0 枚")
        self.processed_total_lbl.setStyleSheet(f"font-size:13px; color:{COL['muted']};")
        top.addWidget(self.progress_hero, 0, Qt.AlignBottom)
        top.addWidget(self.processed_total_lbl, 0, Qt.AlignBottom)
        top.addStretch()
        self.remaining_lbl = QLabel("残り時間 --:--")
        self.remaining_lbl.setStyleSheet(f"font-size:13px; color:{COL['muted']};")
        top.addWidget(self.remaining_lbl, 0, Qt.AlignBottom)
        hero.layout().addLayout(top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("Hero")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        hero.layout().addWidget(self.progress_bar)

        meta = QHBoxLayout()
        self.current_file_label = QLabel("待機中…")
        self.current_file_label.setStyleSheet(f"font-size:12px; color:{COL['faint']};")
        self.chunk_lbl = QLabel("")
        self.chunk_lbl.setStyleSheet(f"font-size:12px; color:{COL['faint']};")
        meta.addWidget(self.current_file_label, 1)
        meta.addWidget(self.chunk_lbl, 0)
        hero.layout().addLayout(meta)
        content.addWidget(hero)

        # 統計タイル
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.card_detected = StatCard("検出成功", "0", "処理済みの 0%")
        self.card_none = StatCard("未検出", "0", "未検出_No_Detection へ")
        self.card_failed = StatCard("失敗", "0", "⚠ 読み込みエラー等", value_color=COL["danger"])
        self.card_rate = StatCard("処理速度", "0.0 枚/秒", "")
        for c in (self.card_detected, self.card_none, self.card_failed, self.card_rate):
            tiles.addWidget(c, 1)
        content.addLayout(tiles)

        # ログ
        log_card = card()
        log_card.layout().addWidget(section_title("処理ログ"))
        self.log_text = QTextEdit()
        self.log_text.setObjectName("Log")
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(180)
        log_card.layout().addWidget(self.log_text)
        content.addWidget(log_card)

        # 停止
        stop_row = QHBoxLayout()
        stop_row.addStretch()
        self.stop_btn = QPushButton("⏸ 停止（チャンク完了後に安全に停止）")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setToolTip("現在処理中のチャンクの完了を待ってから停止します")
        self.stop_btn.setEnabled(False)
        stop_row.addWidget(self.stop_btn)
        content.addLayout(stop_row)

        content.addStretch()
        return page

    # ---------------------------------------------------------- Screen 3
    def _build_results_screen(self) -> QWidget:
        page, content = self._screen_scaffold(
            "結果", "処理が完了すると、ここに検出結果のサマリーと詳細が表示されます。")
        # サブタイトルは処理完了時に更新できるよう参照を保持
        self.results_subtitle = content.itemAt(0).layout().itemAt(1).widget()

        # エクスポート系ボタンをヘッダー右に
        header_row = QHBoxLayout()
        header_row.addStretch()
        self.export_summary_btn = QPushButton("📊 サマリー出力")
        self.export_pivot_btn = QPushButton("📅 日付×種別ピボット")
        self.organize_files_btn = QPushButton("🗂 ファイル振り分け")
        self.export_csv_btn = QPushButton("CSVを開く")
        self.export_csv_btn.setObjectName("Primary")
        self.export_csv_btn.setProperty("compact", True)
        for b in (self.export_summary_btn, self.export_pivot_btn,
                  self.organize_files_btn, self.export_csv_btn):
            b.setEnabled(False)
            header_row.addWidget(b)
        content.addLayout(header_row)

        # サマリータイル
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.card_total = StatCard("総画像数", "0")
        self.card_detected_imgs = StatCard("検出画像数", "0", "検出率 0%")
        self.card_species = StatCard("検出種数", "0", "")
        self.card_time = StatCard("処理時間", "0秒", "")
        for c in (self.card_total, self.card_detected_imgs, self.card_species, self.card_time):
            tiles.addWidget(c, 1)
        content.addLayout(tiles)

        # トップ5
        top5_card = card()
        top5_card.layout().addWidget(section_title("検出数の多い種（トップ5）"))
        self.top5_box = QVBoxLayout()
        self.top5_box.setSpacing(9)
        top5_wrap = QWidget()
        top5_wrap.setMaximumWidth(680)
        top5_wrap.setLayout(self.top5_box)
        top5_card.layout().addWidget(top5_wrap)
        self._render_top5([])
        content.addWidget(top5_card)

        # 詳細テーブル
        detail = card()
        dhead = QHBoxLayout()
        dhead.setSpacing(10)
        dhead.addWidget(section_title("検出結果詳細"), 0)
        dhead.addStretch()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 種名・画像名で絞り込み")
        self.search_input.setFixedWidth(220)
        dhead.addWidget(self.search_input)
        self.cat_combo = QComboBox()
        for label in ("カテゴリ: すべて", "鳥類", "哺乳類", "その他", "未検出"):
            self.cat_combo.addItem(label)
        dhead.addWidget(self.cat_combo)
        detail.layout().addLayout(dhead)

        self.results_table = QTableWidget(0, 6)
        self.results_table.setHorizontalHeaderLabels(
            ["画像名", "種名", "学名", "信頼度", "カテゴリ", "撮影日"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(False)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.verticalHeader().setDefaultSectionSize(46)
        hh = self.results_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.results_table.setColumnWidth(3, 170)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        self.results_table.setColumnWidth(4, 104)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.results_table.setMinimumHeight(300)
        detail.layout().addWidget(self.results_table)

        paging = QHBoxLayout()
        self.prev_page_btn = QPushButton("← 前へ")
        self.prev_page_btn.setEnabled(False)
        self.page_info_label = QLabel("ページ 0 / 0")
        self.page_info_label.setStyleSheet(f"font-size:12px; color:{COL['muted']};")
        self.next_page_btn = QPushButton("次へ →")
        self.next_page_btn.setEnabled(False)
        paging.addWidget(self.prev_page_btn)
        paging.addWidget(self.page_info_label)
        paging.addWidget(self.next_page_btn)
        paging.addStretch()
        detail.layout().addLayout(paging)
        content.addWidget(detail)

        content.addStretch()
        return page

    def _render_top5(self, data: List[tuple]):
        """トップ5横棒グラフを描画。data = [(name, count), ...]（降順）。"""
        while self.top5_box.count():
            item = self.top5_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not data:
            empty = QLabel("まだ結果がありません")
            empty.setStyleSheet(f"font-size:12.5px; color:{COL['faint']};")
            self.top5_box.addWidget(empty)
            return
        top = max(c for _, c in data) or 1
        for name, count in data:
            row = QHBoxLayout()
            row.setSpacing(10)
            nm = QLabel(name)
            nm.setFixedWidth(150)
            nm.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            nm.setStyleSheet(f"font-size:12.5px; color:{COL['muted']};")
            bar = Bar(count / top, height=16)
            cnt = QLabel(f"{count:,}")
            cnt.setFixedWidth(56)
            cnt.setStyleSheet(f"font-size:12.5px; color:{COL['muted']};")
            row.addWidget(nm, 0)
            row.addWidget(bar, 1)
            row.addWidget(cnt, 0)
            w = QWidget()
            w.setLayout(row)
            self.top5_box.addWidget(w)

    # ---------------------------------------------------------- Screen 4
    def _build_settings_screen(self) -> QWidget:
        page, content = self._screen_scaffold(
            "設定", "検出精度とパフォーマンスの設定です。変更は自動的に保存されます。")

        # 検出設定
        det = card()
        det.layout().addWidget(section_title("検出設定"))

        thr_row = self._settings_row(
            "信頼度閾値", "この値未満の検出は「未検出」として扱います")
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(int(round(self.config.confidence_threshold * 100)))
        self.confidence_slider.setFixedWidth(200)
        self.threshold_value_lbl = QLabel(f"{self.config.confidence_threshold:.2f}")
        self.threshold_value_lbl.setStyleSheet(
            f"font-size:13px; background:{COL['paper']}; border:1px solid {COL['border']};"
            f"border-radius:6px; padding:4px 10px;")
        thr_ctrl = QHBoxLayout()
        thr_ctrl.setSpacing(12)
        thr_ctrl.addWidget(self.confidence_slider)
        thr_ctrl.addWidget(self.threshold_value_lbl)
        thr_row.addLayout(thr_ctrl)
        det.layout().addWidget(self._row_wrap(thr_row, first=True))

        country_row = self._settings_row(
            "地域フィルター", "指定した地域に生息する種を優先します")
        self.country_combo = QComboBox()
        self.country_combo.addItems(["JPN", "USA", "CAN", "AUS", "GBR", "None"])
        self.country_combo.setCurrentText(self.config.country_filter)
        country_row.addWidget(self.country_combo, 0)
        det.layout().addWidget(self._row_wrap(country_row))

        batch_row = self._settings_row(
            "バッチサイズ", "1回にまとめて解析する画像数（大きいほど高速・高メモリ）")
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 128)
        self.batch_size_spin.setSingleStep(8)
        self.batch_size_spin.setValue(self.config.batch_size)
        batch_row.addWidget(self.batch_size_spin, 0)
        det.layout().addWidget(self._row_wrap(batch_row))
        content.addWidget(det)

        # パフォーマンス
        perf = card()
        perf.layout().addWidget(section_title("パフォーマンス"))
        self.use_gpu_cb = ToggleSwitch(self.config.use_gpu)
        perf.layout().addWidget(self._toggle_row(
            "GPUを使用", "NVIDIA RTX 4060 を検出しました — 約8倍高速化",
            self.use_gpu_cb, first=True))
        content.addWidget(perf)

        # 外観
        appear = card()
        appear.layout().addWidget(section_title("外観"))
        theme_row = self._settings_row(
            "テーマ", "ライト / ダークを選択（OSに合わせる設定も可）")
        theme_ctrl = QHBoxLayout()
        theme_ctrl.setSpacing(8)
        self.theme_buttons: Dict[str, QPushButton] = {}
        for key, label in (("light", "☀ ライト"), ("dark", "🌙 ダーク"), ("auto", "🖥 自動")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setObjectName("ThemeBtn")
            b.clicked.connect(lambda _=False, k=key: self._set_theme(k))
            self.theme_buttons[key] = b
            theme_ctrl.addWidget(b)
        theme_row.addLayout(theme_ctrl)
        appear.layout().addWidget(self._row_wrap(theme_row, first=True))
        content.addWidget(appear)
        self._refresh_theme_buttons()

        # フッター
        foot = QHBoxLayout()
        foot.addStretch()
        self.reset_settings_btn = QPushButton("デフォルトに戻す")
        self.reset_settings_btn.setObjectName("Ghost")
        foot.addWidget(self.reset_settings_btn)
        content.addLayout(foot)

        content.addStretch()
        return page

    def _set_theme(self, key: str):
        self.theme_value = key
        self._refresh_theme_buttons()
        self._save_config()
        # 注記: 実際の配色切替（ダークモード）は次段階。現状は選択状態の保存のみ。

    def _refresh_theme_buttons(self):
        for key, btn in self.theme_buttons.items():
            btn.setChecked(key == self.theme_value)

    # ------------------------------------------------------------ Navigation
    def set_view(self, name: str):
        self.current_view = name
        self.stack.setCurrentIndex(self.VIEW_STACK[name])
        cur = self.STEP_INDEX[name]
        for key, item in self.step_items.items():
            n = self.STEP_NUM[key]
            item.set_state(active=(key == name), done=(cur > 0 and n < cur))
        self.settings_nav.set_active(name == "settings")

    # ------------------------------------------------------------ Connections
    def setup_connections(self):
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.drop_area.dropped.connect(self._on_files_dropped)
        self.select_output_btn.clicked.connect(self.select_output_folder)
        self.start_btn.clicked.connect(self.start_processing)
        self.stop_btn.clicked.connect(self.stop_processing)

        # 結果画面
        self.export_summary_btn.clicked.connect(self.export_summary)
        self.export_pivot_btn.clicked.connect(self.export_pivot)
        self.organize_files_btn.clicked.connect(self.organize_files)
        self.export_csv_btn.clicked.connect(self.open_results_csv)
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.next_page_btn.clicked.connect(self.next_page)
        self.search_input.textChanged.connect(self._on_search)
        self.cat_combo.currentIndexChanged.connect(self._on_cat_filter)

        # 設定（変更は自動保存）
        self.confidence_slider.valueChanged.connect(self._on_threshold_changed)
        self.batch_size_spin.valueChanged.connect(self._save_config)
        self.country_combo.currentTextChanged.connect(self._save_config)
        self.use_gpu_cb.toggled.connect(self._on_gpu_toggled)
        self.reset_settings_btn.clicked.connect(self.reset_settings)

        # 出力オプション（設定と共有）
        self.create_folders_cb.toggled.connect(self._save_config)
        self.copy_images_cb.toggled.connect(self._save_config)
        self.organize_by_date_cb.toggled.connect(self._save_config)

    def _on_threshold_changed(self, v: int):
        self.threshold_value_lbl.setText(f"{v / 100:.2f}")
        self._save_config()

    def _on_gpu_toggled(self, _checked: bool):
        self._save_config()
        self._refresh_gpu_footer()

    # ------------------------------------------------------------ File select
    def select_files(self):
        file_types = "画像ファイル (*.jpg *.jpeg *.png *.bmp *.tiff);;すべてのファイル (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "画像ファイルを選択", "", file_types)
        if files:
            self.display_selected_files(files)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if folder:
            files = self.processor.find_images(folder)
            self.display_selected_files(files, source=folder)

    def _on_files_dropped(self, paths: List[str]):
        """ドロップされたファイル/フォルダから画像を収集する。"""
        collected: List[str] = []
        for p in paths:
            if os.path.isdir(p):
                collected.extend(self.processor.find_images(p))
            elif os.path.splitext(p)[1].lower() in (
                    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
                collected.append(p)
        if collected:
            src = paths[0] if len(paths) == 1 and os.path.isdir(paths[0]) else None
            self.display_selected_files(collected, source=src)

    def display_selected_files(self, files: List[str], source: Optional[str] = None):
        self.selected_files = files
        n = len(files)
        self.file_count_label.setText(f"選択中の画像 {n:,}枚")
        self.file_path_label.setText(f"（{source}）" if source else "")

        # ファイルテーブル（先頭8件＋残数）
        self.file_table.setRowCount(0)
        preview = files[:8]
        for f in preview:
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            self.file_table.setItem(row, 0, QTableWidgetItem(os.path.basename(f)))
            size_item = QTableWidgetItem(self._human_size(f))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            size_item.setForeground(Qt.gray)
            self.file_table.setItem(row, 1, size_item)
        if n > len(preview):
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            more = QTableWidgetItem(f"… 他 {n - len(preview):,} ファイル")
            more.setForeground(Qt.gray)
            self.file_table.setItem(row, 0, more)
            self.file_table.setItem(row, 1, QTableWidgetItem(""))
        if n == 0:
            self._render_empty_file_table()

        # 推定処理時間
        self._update_est_time(n)
        self.start_btn.setEnabled(n > 0)

    def _human_size(self, path: str) -> str:
        try:
            b = os.path.getsize(path)
        except OSError:
            return ""
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024 or unit == "GB":
                return f"{b:.1f} {unit}" if unit != "B" else f"{b} B"
            b /= 1024
        return ""

    def _update_est_time(self, n: int):
        if n <= 0:
            self.est_time_label.setText("推定処理時間: —")
            return
        rate = 2.4 if self.config.use_gpu else 0.3  # 枚/秒（概算）
        secs = int(n / rate)
        h, rem = divmod(secs, 3600)
        m = rem // 60
        if h:
            t = f"約{h}時間{m}分"
        else:
            t = f"約{m}分" if m else "約1分未満"
        suffix = "（GPU使用時）" if self.config.use_gpu else "（CPU使用時）"
        self.est_time_label.setText(f"推定処理時間: {t}{suffix}")

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "出力フォルダを選択")
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)

    # ------------------------------------------------------------ Processing
    def start_processing(self):
        if not self.selected_files:
            QMessageBox.warning(self, "エラー", "処理する画像ファイルを選択してください")
            return
        if not self.output_folder:
            QMessageBox.warning(self, "エラー", "出力フォルダを選択してください")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._total_to_process = len(self.selected_files)
        self.set_view("processing")

        # 状態リセット
        self.current_page = 0
        self.total_results = 0
        self._results_total_rows = 0
        self._results_unique_species = 0
        self.results_csv_path = None
        self.results_summary = {}
        self.progress_bar.setValue(0)
        self.progress_hero.setText("0%")
        self.processed_total_lbl.setText(f"0 / {self._total_to_process:,} 枚")

        self.processing_thread = ProcessingThread(
            self.processor, self.selected_files, self.output_folder)
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_completed.connect(self.processing_completed)
        self.processing_thread.error_occurred.connect(self.show_error)
        self.processing_thread.start()

        self.log_message("処理を開始しました…")

    def stop_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop_processing()
            self.log_message("処理停止を要求しました（現在のチャンクの完了後に停止します）")
            self.processing_thread.wait(5000)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_message("処理が停止されました")

    def update_progress(self, progress: float, current_file: str, stats: ProcessingStats):
        pct = max(0, min(100, int(progress)))
        self.progress_bar.setValue(pct)
        self.progress_hero.setText(f"{pct}%")

        total = self._total_to_process or stats.processed_images
        self.processed_total_lbl.setText(f"{stats.processed_images:,} / {total:,} 枚")
        self.current_file_label.setText(
            f"処理中: {os.path.basename(current_file)}" if current_file else "処理中…")
        self.chunk_lbl.setText(f"直前の自動保存 {time.strftime('%H:%M')}")

        detected = stats.successful_detections
        failed = stats.failed_images
        none = max(0, stats.processed_images - detected - failed)
        pdone = stats.processed_images or 1
        self.card_detected.set_value(f"{detected:,}", f"処理済みの {detected / pdone * 100:.1f}%")
        self.card_none.set_value(f"{none:,}")
        self.card_failed.set_value(f"{failed:,}")
        self.card_rate.set_value(f"{stats.get_processing_rate():.1f} 枚/秒")

        eta_seconds = stats.get_eta()
        if eta_seconds > 0:
            m, s = divmod(int(eta_seconds), 60)
            self.remaining_lbl.setText(f"残り時間 {m:02d}:{s:02d}")

    def processing_completed(self, summary: Dict[str, Any]):
        self.results_summary = summary
        self.results_csv_path = summary.get('csv_path')
        self.total_results = summary.get('total_processed', 0)

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_hero.setText("100%")
        self.current_file_label.setText("処理完了")

        self.display_results_from_summary(summary)
        self.set_view("results")

        has_csv = self.results_csv_path is not None
        for b in (self.export_csv_btn, self.export_summary_btn,
                  self.export_pivot_btn, self.organize_files_btn):
            b.setEnabled(has_csv)

        total = summary.get('total_processed', 0)
        successful = summary.get('successful', 0)
        skipped = summary.get('skipped', 0)
        stopped = summary.get('stopped', False)

        skipped_msg = f" (スキップ: {skipped})" if skipped else ""
        self.log_message(f"処理が完了しました。{total}個の画像を処理しました{skipped_msg}")

        organize_result = None
        if self.create_folders_cb.isChecked() and self.results_csv_path:
            organize_result = self._auto_organize_files()

        status_msg = "（中断されました）" if stopped else ""
        organize_msg = ""
        if organize_result:
            organize_msg = f"\n振り分けフォルダ数: {organize_result.get('folder_count', 0)}"

        QMessageBox.information(self, "処理完了",
                               f"処理が完了しました{status_msg}\n"
                               f"処理画像数: {total}{skipped_msg}\n"
                               f"検出成功: {successful}\n"
                               f"結果CSV: {self.results_csv_path or 'なし'}{organize_msg}")

    def display_results_from_summary(self, summary: Dict[str, Any]):
        total_images = summary.get('total_processed', 0)
        detected_images = summary.get('successful', 0)
        processing_time = self.processor.get_stats().get_elapsed_time()

        self.card_total.set_value(f"{total_images:,}")
        rate = (detected_images / total_images * 100) if total_images else 0
        self.card_detected_imgs.set_value(f"{detected_images:,}", f"検出率 {rate:.1f}%")

        h, rem = divmod(int(processing_time), 3600)
        m, s = divmod(rem, 60)
        self.card_time.set_value(f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}")

        csv_path = summary.get('csv_path')
        if csv_path:
            self.results_subtitle.setText(
                f"{time.strftime('%Y-%m-%d %H:%M')} 完了 · {os.path.basename(csv_path)}")
            self._refresh_results_metadata(csv_path)
            self.card_species.set_value(f"{self._results_unique_species}", self._cat_breakdown)
            self._render_top5(self._top5)
        else:
            self.results_subtitle.setText("結果CSVがありません")
            self.card_species.set_value("0", "")
            self._render_top5([])

        self.current_page = 0
        self.load_results_page()

    def _refresh_results_metadata(self, csv_path: str) -> None:
        """CSV を1回スキャンして総行数・種数・トップ5・カテゴリ内訳を集計。"""
        total_rows = 0
        species_count: Dict[str, int] = {}
        species_cat: Dict[str, str] = {}
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_rows += 1
                    species = row.get('species', '')
                    if not species:
                        continue
                    name = (row.get('japanese_name') or row.get('common_name') or species)
                    species_count[name] = species_count.get(name, 0) + 1
                    species_cat.setdefault(name, classify_category(row.get('category', '')))
        except OSError as e:
            self.log_message(f"結果メタデータ取得失敗: {e}")

        self._results_total_rows = total_rows
        self._results_unique_species = len(species_count)
        self._top5 = sorted(species_count.items(), key=lambda x: x[1], reverse=True)[:5]

        cat_labels = {"bird": "鳥類", "mammal": "哺乳類", "other": "その他", "none": "未検出"}
        cat_counts: Dict[str, int] = {}
        for name in species_count:
            cat_counts[species_cat[name]] = cat_counts.get(species_cat[name], 0) + 1
        parts = [f"{cat_labels[k]} {cat_counts[k]}"
                 for k in ("bird", "mammal", "other", "none") if cat_counts.get(k)]
        self._cat_breakdown = " · ".join(parts)

    # ------------------------------------------------------------ Results table
    def _on_search(self, text: str):
        self.search_query = text.strip().lower()
        self.current_page = 0
        self.load_results_page()

    def _on_cat_filter(self, index: int):
        self.cat_filter = ["all", "bird", "mammal", "other", "none"][index]
        self.current_page = 0
        self.load_results_page()

    def _row_matches(self, row: Dict[str, str]) -> bool:
        if self.cat_filter != "all":
            cat = "none" if not row.get('species') else classify_category(row.get('category', ''))
            if cat != self.cat_filter:
                return False
        if self.search_query:
            hay = " ".join([
                row.get('image_name', ''), row.get('japanese_name', ''),
                row.get('common_name', ''), row.get('species', ''),
                row.get('scientific_name', ''),
            ]).lower()
            if self.search_query not in hay:
                return False
        return True

    def load_results_page(self):
        self.results_table.setRowCount(0)
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            self.page_info_label.setText("ページ 0 / 0")
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            return

        filtering = bool(self.search_query) or self.cat_filter != "all"
        start_row = self.current_page * self.RESULTS_PER_PAGE
        end_row = start_row + self.RESULTS_PER_PAGE
        rows_to_display: List[Dict[str, str]] = []
        total_rows = 0

        try:
            with open(self.results_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not filtering:
                    total_rows = self._results_total_rows
                    for i, row in enumerate(reader):
                        if i >= end_row:
                            break
                        if i >= start_row:
                            rows_to_display.append(row)
                else:
                    for row in reader:
                        if not self._row_matches(row):
                            continue
                        if start_row <= total_rows < end_row:
                            rows_to_display.append(row)
                        total_rows += 1
        except OSError as e:
            self.log_message(f"結果読み込みエラー: {e}")
            return

        for row in rows_to_display:
            self._add_result_row(row)

        total_pages = max(1, (total_rows + self.RESULTS_PER_PAGE - 1) // self.RESULTS_PER_PAGE)
        self.page_info_label.setText(
            f"ページ {self.current_page + 1} / {total_pages}   "
            f"（{total_rows:,}件 · {self.RESULTS_PER_PAGE}件/ページ）")
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < total_pages - 1)

    def _add_result_row(self, row: Dict[str, str]):
        r = self.results_table.rowCount()
        self.results_table.insertRow(r)

        species = row.get('species', '')
        detected = bool(species)
        jp = (row.get('japanese_name') or row.get('common_name') or species or "検出なし")
        en = row.get('common_name', '')
        sci = row.get('scientific_name', '') or "—"
        cat_key = classify_category(row.get('category', '')) if detected else "none"

        # 画像名
        self.results_table.setItem(r, 0, QTableWidgetItem(row.get('image_name', '')))

        # 種名（和名＋英名）
        name_w = QWidget()
        nv = QVBoxLayout(name_w)
        nv.setContentsMargins(10, 4, 10, 4)
        nv.setSpacing(1)
        jp_lbl = QLabel(jp)
        if detected:
            jp_lbl.setStyleSheet("font-size:13px; font-weight:600;")
        else:
            jp_lbl.setStyleSheet(f"font-size:13px; color:{COL['faint']};")
        nv.addWidget(jp_lbl)
        if detected and en and en != jp:
            en_lbl = QLabel(en)
            en_lbl.setStyleSheet(f"font-size:12px; color:{COL['muted']};")
            nv.addWidget(en_lbl)
        self.results_table.setCellWidget(r, 1, name_w)

        # 学名（イタリック）
        sci_item = QTableWidgetItem(sci)
        f = QFont()
        f.setItalic(True)
        sci_item.setFont(f)
        sci_item.setForeground(Qt.gray)
        self.results_table.setItem(r, 2, sci_item)

        # 信頼度メーター
        try:
            conf = float(row.get('confidence', 0)) if detected else None
            if conf == 0 and not detected:
                conf = None
        except ValueError:
            conf = None
        self.results_table.setCellWidget(r, 3, ConfidenceMeter(conf))

        # カテゴリチップ
        self.results_table.setCellWidget(r, 4, category_chip(cat_key))

        # 撮影日
        date_item = QTableWidgetItem(row.get('image_date', ''))
        date_item.setForeground(Qt.gray)
        self.results_table.setItem(r, 5, date_item)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_results_page()

    def next_page(self):
        self.current_page += 1
        self.load_results_page()

    # ------------------------------------------------------------ Export
    def open_results_csv(self):
        """結果CSVを既定のアプリで開く。"""
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            QMessageBox.warning(self, "エラー", "開く結果CSVがありません")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.results_csv_path))
        self.log_message(f"CSVを開きました: {self.results_csv_path}")

    def export_csv(self):
        """CSV出力（処理済みCSVを出力フォルダへコピー）。"""
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            QMessageBox.warning(self, "エラー", "出力する結果がありません")
            return
        try:
            dest_path = Path(self.output_folder) / os.path.basename(self.results_csv_path)
            if str(dest_path) != self.results_csv_path:
                shutil.copy2(self.results_csv_path, dest_path)
                QMessageBox.information(self, "CSV出力完了", f"CSVファイルをコピーしました:\n{dest_path}")
                self.log_message(f"CSV出力完了: {dest_path}")
            else:
                QMessageBox.information(self, "CSV出力完了",
                                       f"結果CSVは既に出力フォルダにあります:\n{self.results_csv_path}")
        except Exception as e:
            QMessageBox.critical(self, "CSV出力エラー", f"CSV出力中にエラーが発生しました:\n{str(e)}")

    def export_summary(self):
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            QMessageBox.warning(self, "エラー", "出力する結果がありません")
            return
        try:
            exporter = CSVExporter(self.output_folder)
            stats = self.processor.get_stats()
            summary_path = exporter.export_summary_from_csv(self.results_csv_path, stats)
            QMessageBox.information(self, "サマリー出力完了", f"サマリーファイルを出力しました:\n{summary_path}")
            self.log_message(f"サマリー出力完了: {summary_path}")
        except Exception as e:
            QMessageBox.critical(self, "サマリー出力エラー", f"サマリー出力中にエラーが発生しました:\n{str(e)}")

    def export_pivot(self):
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            QMessageBox.warning(self, "エラー", "出力する結果がありません")
            return
        try:
            exporter = CSVExporter(self.output_folder)
            pivot_path = exporter.export_daily_species_pivot(self.results_csv_path)
            QMessageBox.information(self, "ピボット出力完了",
                                    f"日付×種別ピボットを出力しました:\n{pivot_path}")
            self.log_message(f"ピボット出力完了: {pivot_path}")
        except Exception as e:
            QMessageBox.critical(self, "ピボット出力エラー",
                                 f"ピボット出力中にエラーが発生しました:\n{str(e)}")

    def _auto_organize_files(self) -> Optional[Dict[str, Any]]:
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            return None
        try:
            self.log_message("ファイル振り分けを開始…")
            file_manager = FileManager(self.output_folder)
            copy_files = self.copy_images_cb.isChecked()
            organize_by_date = self.organize_by_date_cb.isChecked()

            def _on_organize_progress(processed: int, total: int, current_path: str):
                if total > 0:
                    self.log_message(f"振り分け中: {processed}/{total} ({os.path.basename(current_path)})")

            organization_map = file_manager.organize_images_by_species_from_csv(
                self.results_csv_path, copy_files, organize_by_date=organize_by_date,
                progress_callback=_on_organize_progress,
            )
            summary_path = file_manager.create_species_summary_file(organization_map)
            operation = "コピー" if copy_files else "移動"
            self.log_message(f"ファイル振り分け完了: {len(organization_map)}個のフォルダを作成（{operation}）")
            return {
                'folder_count': len(organization_map),
                'summary_path': summary_path,
                'organization_map': organization_map
            }
        except Exception as e:
            self.log_message(f"ファイル振り分けエラー: {str(e)}")
            return None

    def organize_files(self):
        if not self.results_csv_path or not os.path.exists(self.results_csv_path):
            QMessageBox.warning(self, "エラー", "振り分ける結果がありません")
            return
        reply = QMessageBox.question(self, "ファイル振り分け確認",
                                   "検出結果に基づいて画像ファイルを種別フォルダに振り分けますか?")
        if reply == QMessageBox.Yes:
            result = self._auto_organize_files()
            if result:
                QMessageBox.information(self, "振り分け完了",
                                      f"ファイルの振り分けが完了しました。\n"
                                      f"作成フォルダ数: {result['folder_count']}\n"
                                      f"サマリー: {result['summary_path']}")
            else:
                QMessageBox.critical(self, "振り分けエラー", "ファイル振り分け中にエラーが発生しました")

    # ------------------------------------------------------------ Settings
    def update_config(self):
        self.config.confidence_threshold = self.confidence_slider.value() / 100
        self.config.batch_size = self.batch_size_spin.value()
        self.config.country_filter = self.country_combo.currentText()
        self.config.use_gpu = self.use_gpu_cb.isChecked()
        self.config.create_species_folders = self.create_folders_cb.isChecked()
        self.config.copy_images_to_folders = self.copy_images_cb.isChecked()
        self.config.organize_by_date = self.organize_by_date_cb.isChecked()
        self.config.theme = self.theme_value

    def _save_config(self, *args):
        """設定を反映して自動保存する。"""
        self.update_config()
        self.config_manager.save_config(self.config)

    def reset_settings(self):
        reply = QMessageBox.question(self, "設定リセット確認", "設定をデフォルトに戻しますか?")
        if reply == QMessageBox.Yes:
            self.config = AppConfig.get_default()
            self.theme_value = self.config.theme if self.config.theme in ("light", "dark", "auto") else "light"
            self.load_settings_to_ui()
            self.config_manager.save_config(self.config)
            QMessageBox.information(self, "設定リセット", "設定をデフォルトに戻しました")

    def load_settings_to_ui(self):
        """UIに設定をロード（シグナルを一時ブロックして反映）。"""
        widgets = [self.confidence_slider, self.batch_size_spin, self.country_combo,
                   self.use_gpu_cb, self.create_folders_cb, self.copy_images_cb,
                   self.organize_by_date_cb]
        for w in widgets:
            w.blockSignals(True)
        self.confidence_slider.setValue(int(round(self.config.confidence_threshold * 100)))
        self.threshold_value_lbl.setText(f"{self.config.confidence_threshold:.2f}")
        self.batch_size_spin.setValue(self.config.batch_size)
        self.country_combo.setCurrentText(self.config.country_filter)
        self.use_gpu_cb.setChecked(self.config.use_gpu)
        self.create_folders_cb.setChecked(self.config.create_species_folders)
        self.copy_images_cb.setChecked(self.config.copy_images_to_folders)
        self.organize_by_date_cb.setChecked(self.config.organize_by_date)
        for w in widgets:
            w.blockSignals(False)
        self._refresh_theme_buttons()
        self._refresh_gpu_footer()

    # ------------------------------------------------------------ Misc
    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)
        self.log_message(f"エラー: {title} - {message}")

    def log_message(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(self, "終了確認",
                                       "処理が実行中です。終了しますか？")
            if reply == QMessageBox.Yes:
                self.stop_processing()
                event.accept()
            else:
                event.ignore()
        else:
            self.update_config()
            self.config_manager.save_config(self.config)
            event.accept()
