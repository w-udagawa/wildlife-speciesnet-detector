"""
Wildlife Detector CSV出力モジュール

検出結果をCSV形式で出力します。
既存のCSVファイルからサマリーを生成する機能も提供します。

主要クラス:
    - CSVExporter: CSV出力機能

機能:
    - 検出結果の詳細CSV出力
    - 処理サマリーの生成
    - 種リストの出力
    - CSVベースのサマリー生成（ストリーミング対応）
"""
import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from core.species_detector_direct import DetectionResult
from core.batch_processor import ProcessingStats

class CSVExporter:
    """CSV出力クラス"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def export_results(self, results: List[DetectionResult]) -> str:
        """検出結果をCSVファイルに出力"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"wildlife_detection_results_{timestamp}.csv"
        csv_path = self.output_dir / csv_filename
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    '画像ファイル名',
                    '画像パス',
                    '検出日時',
                    '検出数',
                    '種名_1',
                    '一般名_1', 
                    '学名_1',
                    '信頼度_1',
                    'カテゴリ_1',
                    '種名_2',
                    '一般名_2',
                    '学名_2', 
                    '信頼度_2',
                    'カテゴリ_2',
                    '種名_3',
                    '一般名_3',
                    '学名_3',
                    '信頼度_3',
                    'カテゴリ_3',
                    '備考'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    # 基本情報
                    row = {
                        '画像ファイル名': result.image_name,
                        '画像パス': result.image_path,
                        '検出日時': result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        '検出数': len(result.detections),
                        '備考': ''
                    }
                    
                    # 検出結果（最大3つまで）
                    for i, detection in enumerate(result.detections[:3], 1):
                        row[f'種名_{i}'] = detection.get('species', '')
                        row[f'一般名_{i}'] = detection.get('common_name', '')
                        row[f'学名_{i}'] = detection.get('scientific_name', '')
                        row[f'信頼度_{i}'] = f"{detection.get('confidence', 0):.4f}"
                        row[f'カテゴリ_{i}'] = detection.get('category', '')
                    
                    # 検出がない場合の備考
                    if not result.has_detections():
                        row['備考'] = '野生生物が検出されませんでした'
                    elif len(result.detections) > 3:
                        row['備考'] = f'追加で{len(result.detections) - 3}個の検出があります'
                    
                    writer.writerow(row)
            
            self.logger.info(f"CSV出力完了: {csv_path}")
            return str(csv_path)
            
        except Exception as e:
            self.logger.error(f"CSV出力エラー: {str(e)}")
            raise
    
    def export_summary(self, results: List[DetectionResult], stats: ProcessingStats) -> str:
        """サマリー情報をCSVファイルに出力"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"wildlife_detection_summary_{timestamp}.csv"
        summary_path = self.output_dir / summary_filename
        
        try:
            # 統計情報の計算
            total_images = len(results)
            detected_images = sum(1 for r in results if r.has_detections())
            total_detections = sum(len(r.detections) for r in results)
            
            # 種別統計
            species_count = {}
            category_count = {}
            
            for result in results:
                for detection in result.detections:
                    species = detection.get('species', 'Unknown')
                    category = detection.get('category', 'Unknown')
                    
                    species_count[species] = species_count.get(species, 0) + 1
                    category_count[category] = category_count.get(category, 0) + 1
            
            with open(summary_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # ヘッダー
                writer.writerow(['Wildlife Detection Summary Report'])
                writer.writerow(['Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow([])
                
                # 基本統計
                writer.writerow(['基本統計'])
                writer.writerow(['項目', '値'])
                writer.writerow(['総画像数', total_images])
                writer.writerow(['検出成功画像数', detected_images])
                writer.writerow(['検出失敗画像数', total_images - detected_images])
                writer.writerow(['総検出数', total_detections])
                writer.writerow(['成功率 (%)', f"{(detected_images/total_images*100):.1f}" if total_images > 0 else "0"])
                writer.writerow(['処理時間 (秒)', f"{stats.get_elapsed_time():.1f}"])
                writer.writerow(['処理速度 (画像/秒)', f"{stats.get_processing_rate():.2f}"])
                writer.writerow([])
                
                # 種別統計
                if species_count:
                    writer.writerow(['検出種別統計'])
                    writer.writerow(['種名', '検出回数', '割合 (%)'])
                    
                    sorted_species = sorted(species_count.items(), key=lambda x: x[1], reverse=True)
                    for species, count in sorted_species:
                        percentage = (count / total_detections * 100) if total_detections > 0 else 0
                        writer.writerow([species, count, f"{percentage:.1f}"])
                    writer.writerow([])
                
                # カテゴリ統計
                if category_count:
                    writer.writerow(['カテゴリ別統計'])
                    writer.writerow(['カテゴリ', '検出回数', '割合 (%)'])
                    
                    sorted_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)
                    for category, count in sorted_categories:
                        percentage = (count / total_detections * 100) if total_detections > 0 else 0
                        writer.writerow([category, count, f"{percentage:.1f}"])
                    writer.writerow([])
                
                # 信頼度統計
                writer.writerow(['信頼度統計'])
                writer.writerow(['信頼度範囲', '検出数'])
                
                confidence_ranges = {
                    '0.9-1.0 (非常に高い)': 0,
                    '0.7-0.9 (高い)': 0,
                    '0.5-0.7 (中程度)': 0,
                    '0.3-0.5 (低い)': 0,
                    '0.0-0.3 (非常に低い)': 0
                }
                
                for result in results:
                    for detection in result.detections:
                        confidence = detection.get('confidence', 0)
                        if confidence >= 0.9:
                            confidence_ranges['0.9-1.0 (非常に高い)'] += 1
                        elif confidence >= 0.7:
                            confidence_ranges['0.7-0.9 (高い)'] += 1
                        elif confidence >= 0.5:
                            confidence_ranges['0.5-0.7 (中程度)'] += 1
                        elif confidence >= 0.3:
                            confidence_ranges['0.3-0.5 (低い)'] += 1
                        else:
                            confidence_ranges['0.0-0.3 (非常に低い)'] += 1
                
                for range_name, count in confidence_ranges.items():
                    writer.writerow([range_name, count])
            
            self.logger.info(f"サマリー出力完了: {summary_path}")
            return str(summary_path)

        except Exception as e:
            self.logger.error(f"サマリー出力エラー: {str(e)}")
            raise

    def export_summary_from_csv(self, source_csv_path: str, stats: ProcessingStats) -> str:
        """CSVファイルからサマリー情報を生成して出力（ストリーミング版）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"wildlife_detection_summary_{timestamp}.csv"
        summary_path = self.output_dir / summary_filename

        try:
            # 統計情報の計算（CSVを1行ずつ読み込み）
            total_images = 0
            detected_images = 0
            total_detections = 0
            species_count = {}
            category_count = {}
            confidence_ranges = {
                '0.9-1.0 (非常に高い)': 0,
                '0.7-0.9 (高い)': 0,
                '0.5-0.7 (中程度)': 0,
                '0.3-0.5 (低い)': 0,
                '0.0-0.3 (非常に低い)': 0
            }

            with open(source_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    total_images += 1
                    species = row.get('species', '')
                    category = row.get('category', '')
                    confidence_str = row.get('confidence', '0')

                    try:
                        confidence = float(confidence_str)
                    except ValueError:
                        confidence = 0

                    if species:
                        detected_images += 1
                        total_detections += 1
                        species_count[species] = species_count.get(species, 0) + 1

                        if category:
                            category_count[category] = category_count.get(category, 0) + 1

                        # 信頼度範囲の集計
                        if confidence >= 0.9:
                            confidence_ranges['0.9-1.0 (非常に高い)'] += 1
                        elif confidence >= 0.7:
                            confidence_ranges['0.7-0.9 (高い)'] += 1
                        elif confidence >= 0.5:
                            confidence_ranges['0.5-0.7 (中程度)'] += 1
                        elif confidence >= 0.3:
                            confidence_ranges['0.3-0.5 (低い)'] += 1
                        else:
                            confidence_ranges['0.0-0.3 (非常に低い)'] += 1

            # サマリーCSVの出力
            with open(summary_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # ヘッダー
                writer.writerow(['Wildlife Detection Summary Report'])
                writer.writerow(['Generated:', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                writer.writerow(['Source CSV:', source_csv_path])
                writer.writerow([])

                # 基本統計
                writer.writerow(['基本統計'])
                writer.writerow(['項目', '値'])
                writer.writerow(['総画像数', total_images])
                writer.writerow(['検出成功画像数', detected_images])
                writer.writerow(['検出失敗画像数', total_images - detected_images])
                writer.writerow(['総検出数', total_detections])
                writer.writerow(['成功率 (%)', f"{(detected_images/total_images*100):.1f}" if total_images > 0 else "0"])
                writer.writerow(['処理時間 (秒)', f"{stats.get_elapsed_time():.1f}"])
                writer.writerow(['処理速度 (画像/秒)', f"{stats.get_processing_rate():.2f}"])
                writer.writerow([])

                # 種別統計
                if species_count:
                    writer.writerow(['検出種別統計'])
                    writer.writerow(['種名', '検出回数', '割合 (%)'])

                    sorted_species = sorted(species_count.items(), key=lambda x: x[1], reverse=True)
                    for species, count in sorted_species:
                        percentage = (count / total_detections * 100) if total_detections > 0 else 0
                        writer.writerow([species, count, f"{percentage:.1f}"])
                    writer.writerow([])

                # カテゴリ統計
                if category_count:
                    writer.writerow(['カテゴリ別統計'])
                    writer.writerow(['カテゴリ', '検出回数', '割合 (%)'])

                    sorted_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)
                    for category, count in sorted_categories:
                        percentage = (count / total_detections * 100) if total_detections > 0 else 0
                        writer.writerow([category, count, f"{percentage:.1f}"])
                    writer.writerow([])

                # 信頼度統計
                writer.writerow(['信頼度統計'])
                writer.writerow(['信頼度範囲', '検出数'])

                for range_name, count in confidence_ranges.items():
                    writer.writerow([range_name, count])

            self.logger.info(f"サマリー出力完了: {summary_path}")
            return str(summary_path)

        except Exception as e:
            self.logger.error(f"サマリー出力エラー: {str(e)}")
            raise

    def export_species_list(self, results: List[DetectionResult]) -> str:
        """検出された種のリストをCSVファイルに出力"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        species_filename = f"wildlife_species_list_{timestamp}.csv"
        species_path = self.output_dir / species_filename
        
        try:
            # 種情報の収集
            species_info = {}
            
            for result in results:
                for detection in result.detections:
                    species = detection.get('species', 'Unknown')
                    
                    if species not in species_info:
                        species_info[species] = {
                            'species': species,
                            'common_name': detection.get('common_name', ''),
                            'scientific_name': detection.get('scientific_name', ''),
                            'category': detection.get('category', ''),
                            'detection_count': 0,
                            'max_confidence': 0,
                            'avg_confidence': 0,
                            'confidences': []
                        }
                    
                    info = species_info[species]
                    info['detection_count'] += 1
                    confidence = detection.get('confidence', 0)
                    info['confidences'].append(confidence)
                    info['max_confidence'] = max(info['max_confidence'], confidence)
            
            # 平均信頼度の計算
            for info in species_info.values():
                if info['confidences']:
                    info['avg_confidence'] = sum(info['confidences']) / len(info['confidences'])
            
            with open(species_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    '種名',
                    '一般名',
                    '学名', 
                    'カテゴリ',
                    '検出回数',
                    '最高信頼度',
                    '平均信頼度'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # 検出回数順でソート
                sorted_species = sorted(species_info.values(), 
                                      key=lambda x: x['detection_count'], 
                                      reverse=True)
                
                for info in sorted_species:
                    writer.writerow({
                        '種名': info['species'],
                        '一般名': info['common_name'],
                        '学名': info['scientific_name'],
                        'カテゴリ': info['category'],
                        '検出回数': info['detection_count'],
                        '最高信頼度': f"{info['max_confidence']:.4f}",
                        '平均信頼度': f"{info['avg_confidence']:.4f}"
                    })
            
            self.logger.info(f"種リスト出力完了: {species_path}")
            return str(species_path)
            
        except Exception as e:
            self.logger.error(f"種リスト出力エラー: {str(e)}")
            raise
