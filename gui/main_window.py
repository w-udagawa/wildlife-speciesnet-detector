"""
メインGUIモジュール - 元のファイルのバックアップ
Wildlife Detectorのメインウィンドウ（2025-06-06バックアップ）
"""
import sys
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import threading
import time

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QGridLayout, QPushButton, QLabel, 
                              QFileDialog, QTextEdit, QProgressBar, QTabWidget,
                              QTableWidget, QTableWidgetItem, QGroupBox,
                              QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
                              QMessageBox, QSplitter, QFrame, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

from core.config import ConfigManager, AppConfig
from core.batch_processor import BatchProcessor, ProcessingStats
from core.species_detector import DetectionResult
from utils.csv_exporter import CSVExporter
from utils.file_manager import FileManager

class ProcessingThread(QThread):
    """バッチ処理用スレッド"""
    
    progress_updated = Signal(float, str, object)  # progress, current_file, stats
    processing_completed = Signal(list)  # results
    error_occurred = Signal(str, str)  # title, message
    
    def __init__(self, processor: BatchProcessor, image_paths: List[str]):
        super().__init__()
        self.processor = processor
        self.image_paths = image_paths
        self.results = []
    
    def run(self):
        """処理スレッドの実行"""
        try:
            # コールバック設定
            self.processor.set_progress_callback(self._on_progress)
            self.processor.set_error_callback(self._on_error)
            
            # バッチ処理実行
            self.results = self.processor.process_images(self.image_paths)
            
            # 完了シグナル
            self.processing_completed.emit(self.results)
            
        except Exception as e:
            self.error_occurred.emit("処理エラー", str(e))
    
    def _on_progress(self, progress: float, current_file: str, stats: ProcessingStats):
        """進捗更新コールバック"""
        self.progress_updated.emit(progress, current_file, stats)
    
    def _on_error(self, file_path: str, error_message: str):
        """エラーコールバック"""
        self.error_occurred.emit(f"ファイル処理エラー: {os.path.basename(file_path)}", error_message)
    
    def stop_processing(self):
        """処理停止"""
        if self.processor:
            self.processor.stop_processing()

class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self):
        super().__init__()
        
        # 設定管理
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # 処理関連
        self.processor = BatchProcessor(self.config)
        self.processing_thread = None
        self.current_results = []
        
        # UI初期化
        self.init_ui()
        self.setup_connections()
        
        # ウィンドウ設定
        self.setWindowTitle("Wildlife Detector - 野生生物検出アプリケーション")
        self.resize(*self.config.window_size)
        self.setMinimumSize(800, 600)
    
    def init_ui(self):
        """UI初期化"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 各タブの作成
        self.create_input_tab()
        self.create_processing_tab()
        self.create_results_tab()
        self.create_settings_tab()
        
        # ステータスバー
        self.statusBar().showMessage("準備完了")
    
    def create_input_tab(self):
        """入力タブの作成"""
        input_widget = QWidget()
        layout = QVBoxLayout(input_widget)
        
        # ファイル選択グループ
        file_group = QGroupBox("画像ファイル選択")
        file_layout = QVBoxLayout(file_group)
        
        # ファイル選択ボタン
        button_layout = QHBoxLayout()
        
        self.select_files_btn = QPushButton("ファイルを選択")
        self.select_files_btn.clicked.connect(self.select_files)
        button_layout.addWidget(self.select_files_btn)
        
        self.select_folder_btn = QPushButton("フォルダを選択")
        self.select_folder_btn.clicked.connect(self.select_folder)
        button_layout.addWidget(self.select_folder_btn)
        
        button_layout.addStretch()
        file_layout.addLayout(button_layout)
        
        # 選択されたファイル一覧
        self.file_list = QTextEdit()
        self.file_list.setMaximumHeight(200)
        self.file_list.setPlaceholderText("選択されたファイルがここに表示されます...")
        file_layout.addWidget(self.file_list)
        
        # ファイル情報
        self.file_info_label = QLabel("ファイル: 0個選択")
        file_layout.addWidget(self.file_info_label)
        
        layout.addWidget(file_group)
        
        # 出力設定グループ
        output_group = QGroupBox("出力設定")
        output_layout = QGridLayout(output_group)
        
        output_layout.addWidget(QLabel("出力フォルダ:"), 0, 0)
        
        output_folder_layout = QHBoxLayout()
        self.output_folder_label = QLabel("未選択")
        self.select_output_btn = QPushButton("選択")
        self.select_output_btn.clicked.connect(self.select_output_folder)
        
        output_folder_layout.addWidget(self.output_folder_label)
        output_folder_layout.addWidget(self.select_output_btn)
        output_layout.addLayout(output_folder_layout, 0, 1)
        
        # 出力オプション
        self.create_folders_cb = QCheckBox("種別フォルダを作成")
        self.create_folders_cb.setChecked(self.config.create_species_folders)
        output_layout.addWidget(self.create_folders_cb, 1, 0, 1, 2)
        
        self.copy_images_cb = QCheckBox("画像をコピー（チェックなしの場合は移動）")
        self.copy_images_cb.setChecked(self.config.copy_images_to_folders)
        output_layout.addWidget(self.copy_images_cb, 2, 0, 1, 2)
        
        layout.addWidget(output_group)
        
        # 処理開始ボタン
        self.start_btn = QPushButton("検出処理開始")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; }")
        layout.addWidget(self.start_btn)
        
        layout.addStretch()
        self.tab_widget.addTab(input_widget, "入力・設定")
    
    def create_processing_tab(self):
        """処理タブの作成"""
        processing_widget = QWidget()
        layout = QVBoxLayout(processing_widget)
        
        # 進捗グループ
        progress_group = QGroupBox("処理進捗")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.current_file_label = QLabel("待機中...")
        progress_layout.addWidget(self.current_file_label)
        
        # 統計情報
        stats_layout = QGridLayout()
        
        self.processed_label = QLabel("処理済み: 0")
        self.detected_label = QLabel("検出成功: 0")
        self.failed_label = QLabel("失敗: 0")
        self.rate_label = QLabel("処理速度: 0.0 画像/秒")
        self.eta_label = QLabel("残り時間: --:--")
        
        stats_layout.addWidget(self.processed_label, 0, 0)
        stats_layout.addWidget(self.detected_label, 0, 1)
        stats_layout.addWidget(self.failed_label, 1, 0)
        stats_layout.addWidget(self.rate_label, 1, 1)
        stats_layout.addWidget(self.eta_label, 2, 0, 1, 2)
        
        progress_layout.addLayout(stats_layout)
        layout.addWidget(progress_group)
        
        # 制御ボタン
        control_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("一時停止")
        self.pause_btn.setEnabled(False)
        control_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # ログ表示
        log_group = QGroupBox("処理ログ")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(300)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        self.tab_widget.addTab(processing_widget, "処理進捗")
    
    def create_results_tab(self):
        """結果タブの作成"""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)
        
        # 結果サマリー
        summary_group = QGroupBox("処理結果サマリー")
        summary_layout = QGridLayout(summary_group)
        
        self.total_images_label = QLabel("総画像数: 0")
        self.detected_images_label = QLabel("検出画像数: 0")
        self.unique_species_label = QLabel("検出種数: 0")
        self.processing_time_label = QLabel("処理時間: 0秒")
        
        summary_layout.addWidget(self.total_images_label, 0, 0)
        summary_layout.addWidget(self.detected_images_label, 0, 1)
        summary_layout.addWidget(self.unique_species_label, 1, 0)
        summary_layout.addWidget(self.processing_time_label, 1, 1)
        
        layout.addWidget(summary_group)
        
        # 結果テーブル
        table_group = QGroupBox("検出結果詳細")
        table_layout = QVBoxLayout(table_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "画像名", "種名", "一般名", "学名", "信頼度", "カテゴリ", "検出数"
        ])
        table_layout.addWidget(self.results_table)
        
        layout.addWidget(table_group)
        
        # エクスポートボタン
        export_layout = QHBoxLayout()
        
        self.export_csv_btn = QPushButton("CSV出力")
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.export_csv_btn.setEnabled(False)
        export_layout.addWidget(self.export_csv_btn)
        
        self.export_summary_btn = QPushButton("サマリー出力")
        self.export_summary_btn.clicked.connect(self.export_summary)
        self.export_summary_btn.setEnabled(False)
        export_layout.addWidget(self.export_summary_btn)
        
        self.organize_files_btn = QPushButton("ファイル振り分け")
        self.organize_files_btn.clicked.connect(self.organize_files)
        self.organize_files_btn.setEnabled(False)
        export_layout.addWidget(self.organize_files_btn)
        
        export_layout.addStretch()
        layout.addLayout(export_layout)
        
        self.tab_widget.addTab(results_widget, "結果")
    
    def create_settings_tab(self):
        """設定タブの作成"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # 検出設定
        detection_group = QGroupBox("検出設定")
        detection_layout = QGridLayout(detection_group)
        
        detection_layout.addWidget(QLabel("信頼度閾値:"), 0, 0)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.01)
        self.confidence_spin.setValue(self.config.confidence_threshold)
        detection_layout.addWidget(self.confidence_spin, 0, 1)
        
        detection_layout.addWidget(QLabel("バッチサイズ:"), 1, 0)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 128)
        self.batch_size_spin.setValue(self.config.batch_size)
        detection_layout.addWidget(self.batch_size_spin, 1, 1)
        
        detection_layout.addWidget(QLabel("地域フィルター:"), 2, 0)
        self.country_combo = QComboBox()
        self.country_combo.addItems(["JPN", "USA", "CAN", "AUS", "GBR", "None"])
        self.country_combo.setCurrentText(self.config.country_filter)
        detection_layout.addWidget(self.country_combo, 2, 1)
        
        layout.addWidget(detection_group)
        
        # パフォーマンス設定
        performance_group = QGroupBox("パフォーマンス設定")
        performance_layout = QGridLayout(performance_group)
        
        performance_layout.addWidget(QLabel("最大ワーカー数:"), 0, 0)
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 16)
        self.workers_spin.setValue(self.config.max_workers)
        performance_layout.addWidget(self.workers_spin, 0, 1)
        
        self.use_gpu_cb = QCheckBox("GPU使用")
        self.use_gpu_cb.setChecked(self.config.use_gpu)
        performance_layout.addWidget(self.use_gpu_cb, 1, 0, 1, 2)
        
        layout.addWidget(performance_group)
        
        # 設定保存ボタン
        settings_buttons = QHBoxLayout()
        
        save_settings_btn = QPushButton("設定を保存")
        save_settings_btn.clicked.connect(self.save_settings)
        settings_buttons.addWidget(save_settings_btn)
        
        reset_settings_btn = QPushButton("デフォルトに戻す")
        reset_settings_btn.clicked.connect(self.reset_settings)
        settings_buttons.addWidget(reset_settings_btn)
        
        settings_buttons.addStretch()
        layout.addLayout(settings_buttons)
        
        layout.addStretch()
        self.tab_widget.addTab(settings_widget, "設定")
    
    def setup_connections(self):
        """シグナル・スロット接続"""
        # 設定変更の監視
        self.confidence_spin.valueChanged.connect(self.update_config)
        self.batch_size_spin.valueChanged.connect(self.update_config)
        self.country_combo.currentTextChanged.connect(self.update_config)
        self.workers_spin.valueChanged.connect(self.update_config)
        self.use_gpu_cb.toggled.connect(self.update_config)
    
    def select_files(self):
        """ファイル選択ダイアログ"""
        file_types = "画像ファイル (*.jpg *.jpeg *.png *.bmp *.tiff);;すべてのファイル (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "画像ファイルを選択", "", file_types)
        
        if files:
            self.display_selected_files(files)
    
    def select_folder(self):
        """フォルダ選択ダイアログ"""
        folder = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        
        if folder:
            # フォルダ内の画像を検索
            files = self.processor.find_images(folder)
            self.display_selected_files(files)
    
    def display_selected_files(self, files: List[str]):
        """選択されたファイルを表示"""
        self.selected_files = files
        
        # ファイル一覧の更新
        file_list_text = "\n".join([os.path.basename(f) for f in files[:10]])
        if len(files) > 10:
            file_list_text += f"\n... 他 {len(files) - 10} ファイル"
        
        self.file_list.setPlainText(file_list_text)
        self.file_info_label.setText(f"ファイル: {len(files)}個選択")
        
        # 処理開始ボタンの有効化
        self.start_btn.setEnabled(len(files) > 0)
    
    def select_output_folder(self):
        """出力フォルダ選択"""
        folder = QFileDialog.getExistingDirectory(self, "出力フォルダを選択")
        
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)
    
    def start_processing(self):
        """処理開始"""
        if not hasattr(self, 'selected_files') or not self.selected_files:
            QMessageBox.warning(self, "エラー", "処理する画像ファイルを選択してください")
            return
        
        if not hasattr(self, 'output_folder'):
            QMessageBox.warning(self, "エラー", "出力フォルダを選択してください")
            return
        
        # UI状態の更新
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.tab_widget.setCurrentIndex(1)  # 処理タブに切り替え
        
        # 処理スレッドの開始
        self.processing_thread = ProcessingThread(self.processor, self.selected_files)
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_completed.connect(self.processing_completed)
        self.processing_thread.error_occurred.connect(self.show_error)
        self.processing_thread.start()
        
        self.log_message("処理を開始しました...")
    
    def stop_processing(self):
        """処理停止"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop_processing()
            self.log_message("処理停止要求を送信しました...")
            
            # スレッドの終了を待機
            self.processing_thread.wait(5000)  # 5秒でタイムアウト
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_message("処理が停止されました")
    
    def update_progress(self, progress: float, current_file: str, stats: ProcessingStats):
        """進捗更新"""
        self.progress_bar.setValue(int(progress))
        self.current_file_label.setText(f"処理中: {os.path.basename(current_file)}")
        
        # 統計情報の更新
        self.processed_label.setText(f"処理済み: {stats.processed_images}")
        self.detected_label.setText(f"検出成功: {stats.successful_detections}")
        self.failed_label.setText(f"失敗: {stats.failed_images}")
        self.rate_label.setText(f"処理速度: {stats.get_processing_rate():.1f} 画像/秒")
        
        # 残り時間
        eta_seconds = stats.get_eta()
        if eta_seconds > 0:
            eta_minutes = int(eta_seconds // 60)
            eta_seconds = int(eta_seconds % 60)
            self.eta_label.setText(f"残り時間: {eta_minutes:02d}:{eta_seconds:02d}")
    
    def processing_completed(self, results: List[DetectionResult]):
        """処理完了"""
        self.current_results = results
        
        # UI状態の復元
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.current_file_label.setText("処理完了")
        
        # 結果の表示
        self.display_results(results)
        
        # 結果タブに切り替え
        self.tab_widget.setCurrentIndex(2)
        
        # エクスポートボタンの有効化
        self.export_csv_btn.setEnabled(True)
        self.export_summary_btn.setEnabled(True)
        self.organize_files_btn.setEnabled(True)
        
        self.log_message(f"処理が完了しました。{len(results)}個の画像を処理しました")
        
        # 完了メッセージ
        QMessageBox.information(self, "処理完了", 
                               f"処理が完了しました。\n"
                               f"処理画像数: {len(results)}\n"
                               f"検出成功: {sum(1 for r in results if r.has_detections())}")
    
    def display_results(self, results: List[DetectionResult]):
        """結果表示"""
        # サマリー更新
        total_images = len(results)
        detected_images = sum(1 for r in results if r.has_detections())
        
        # 種類の集計
        species_set = set()
        for result in results:
            for detection in result.detections:
                species_set.add(detection.get('species', 'Unknown'))
        
        processing_time = self.processor.get_stats().get_elapsed_time()
        
        self.total_images_label.setText(f"総画像数: {total_images}")
        self.detected_images_label.setText(f"検出画像数: {detected_images}")
        self.unique_species_label.setText(f"検出種数: {len(species_set)}")
        self.processing_time_label.setText(f"処理時間: {processing_time:.1f}秒")
        
        # テーブル更新
        self.update_results_table(results)
    
    def update_results_table(self, results: List[DetectionResult]):
        """結果テーブル更新"""
        # テーブルのクリア
        self.results_table.setRowCount(0)
        
        row = 0
        for result in results:
            if result.has_detections():
                for detection in result.detections:
                    self.results_table.insertRow(row)
                    
                    self.results_table.setItem(row, 0, QTableWidgetItem(result.image_name))
                    self.results_table.setItem(row, 1, QTableWidgetItem(detection.get('species', '')))
                    self.results_table.setItem(row, 2, QTableWidgetItem(detection.get('common_name', '')))
                    self.results_table.setItem(row, 3, QTableWidgetItem(detection.get('scientific_name', '')))
                    self.results_table.setItem(row, 4, QTableWidgetItem(f"{detection.get('confidence', 0):.3f}"))
                    self.results_table.setItem(row, 5, QTableWidgetItem(detection.get('category', '')))
                    self.results_table.setItem(row, 6, QTableWidgetItem(str(len(result.detections))))
                    
                    row += 1
            else:
                # 検出なしの行
                self.results_table.insertRow(row)
                self.results_table.setItem(row, 0, QTableWidgetItem(result.image_name))
                self.results_table.setItem(row, 1, QTableWidgetItem("検出なし"))
                for col in range(2, 7):
                    self.results_table.setItem(row, col, QTableWidgetItem(""))
                row += 1
        
        # 列幅の調整
        self.results_table.resizeColumnsToContents()
    
    def export_csv(self):
        """CSV出力"""
        if not self.current_results:
            return
        
        try:
            exporter = CSVExporter(self.output_folder)
            csv_path = exporter.export_results(self.current_results)
            
            QMessageBox.information(self, "CSV出力完了", f"CSVファイルを出力しました:\n{csv_path}")
            self.log_message(f"CSV出力完了: {csv_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "CSV出力エラー", f"CSV出力中にエラーが発生しました:\n{str(e)}")
    
    def export_summary(self):
        """サマリー出力"""
        if not self.current_results:
            return
        
        try:
            exporter = CSVExporter(self.output_folder)
            stats = self.processor.get_stats()
            summary_path = exporter.export_summary(self.current_results, stats)
            
            QMessageBox.information(self, "サマリー出力完了", f"サマリーファイルを出力しました:\n{summary_path}")
            self.log_message(f"サマリー出力完了: {summary_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "サマリー出力エラー", f"サマリー出力中にエラーが発生しました:\n{str(e)}")
    
    def organize_files(self):
        """ファイル振り分け"""
        if not self.current_results:
            return
        
        reply = QMessageBox.question(self, "ファイル振り分け確認", 
                                   "検出結果に基づいて画像ファイルを種別フォルダに振り分けますか?")
        
        if reply == QMessageBox.Yes:
            try:
                file_manager = FileManager(self.output_folder)
                copy_files = self.copy_images_cb.isChecked()
                
                organization_map = file_manager.organize_images_by_species(
                    self.current_results, copy_files
                )
                
                summary_path = file_manager.create_species_summary_file(organization_map)
                
                QMessageBox.information(self, "振り分け完了", 
                                      f"ファイルの振り分けが完了しました。\n"
                                      f"作成フォルダ数: {len(organization_map)}\n"
                                      f"サマリー: {summary_path}")
                
                self.log_message(f"ファイル振り分け完了: {len(organization_map)}個のフォルダを作成")
                
            except Exception as e:
                QMessageBox.critical(self, "振り分けエラー", f"ファイル振り分け中にエラーが発生しました:\n{str(e)}")
    
    def update_config(self):
        """設定更新"""
        self.config.confidence_threshold = self.confidence_spin.value()
        self.config.batch_size = self.batch_size_spin.value()
        self.config.country_filter = self.country_combo.currentText()
        self.config.max_workers = self.workers_spin.value()
        self.config.use_gpu = self.use_gpu_cb.isChecked()
        self.config.create_species_folders = self.create_folders_cb.isChecked()
        self.config.copy_images_to_folders = self.copy_images_cb.isChecked()
    
    def save_settings(self):
        """設定保存"""
        self.update_config()
        if self.config_manager.save_config():
            QMessageBox.information(self, "設定保存", "設定が保存されました")
        else:
            QMessageBox.warning(self, "設定保存エラー", "設定の保存に失敗しました")
    
    def reset_settings(self):
        """設定リセット"""
        reply = QMessageBox.question(self, "設定リセット確認", "設定をデフォルトに戻しますか?")
        
        if reply == QMessageBox.Yes:
            self.config = AppConfig.get_default()
            self.load_settings_to_ui()
            QMessageBox.information(self, "設定リセット", "設定をデフォルトに戻しました")
    
    def load_settings_to_ui(self):
        """UIに設定をロード"""
        self.confidence_spin.setValue(self.config.confidence_threshold)
        self.batch_size_spin.setValue(self.config.batch_size)
        self.country_combo.setCurrentText(self.config.country_filter)
        self.workers_spin.setValue(self.config.max_workers)
        self.use_gpu_cb.setChecked(self.config.use_gpu)
        self.create_folders_cb.setChecked(self.config.create_species_folders)
        self.copy_images_cb.setChecked(self.config.copy_images_to_folders)
    
    def show_error(self, title: str, message: str):
        """エラー表示"""
        QMessageBox.critical(self, title, message)
        self.log_message(f"エラー: {title} - {message}")
    
    def log_message(self, message: str):
        """ログメッセージ追加"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def closeEvent(self, event):
        """ウィンドウクローズイベント"""
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(self, "終了確認", 
                                       "処理が実行中です。終了しますか？")
            if reply == QMessageBox.Yes:
                self.stop_processing()
                event.accept()
            else:
                event.ignore()
        else:
            # 設定の保存
            self.update_config()
            self.config_manager.save_config()
            event.accept()
