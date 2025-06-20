"""
SpeciesNet統合モジュール（テスト用モックアップ付き）
Google SpeciesNetを使用した野生生物検出機能
"""
import os
import sys
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import logging
import random
import time
from datetime import datetime

# SpeciesNetの実際のインポートを試行
try:
    import speciesnet
    from speciesnet import SpeciesNet
    SPECIESNET_AVAILABLE = True
    logging.info("SpeciesNet が正常にインポートされました")
except ImportError:
    SPECIESNET_AVAILABLE = False
    logging.warning("SpeciesNet がインストールされていません。モックアップモードで動作します")

class DetectionResult:
    """検出結果を格納するクラス"""
    
    def __init__(self, image_path: str, detections: List[Dict[str, Any]]):
        self.image_path = image_path
        self.image_name = os.path.basename(image_path)
        self.detections = detections
        self.timestamp = datetime.now()
    
    def get_best_detection(self) -> Optional[Dict[str, Any]]:
        """最も信頼度の高い検出結果を取得"""
        if not self.detections:
            return None
        return max(self.detections, key=lambda x: x.get('confidence', 0))
    
    def has_detections(self) -> bool:
        """検出結果があるかどうか"""
        return len(self.detections) > 0
    
    def get_species_count(self) -> int:
        """検出された種の数"""
        species_set = set()
        for detection in self.detections:
            if 'species' in detection:
                species_set.add(detection['species'])
        return len(species_set)

class MockSpeciesNet:
    """SpeciesNetのモックアップクラス（テスト用）"""
    
    def __init__(self):
        # 日本の代表的な野生生物データベース
        self.japanese_species = [
            {
                'species': 'Passer montanus',
                'common_name': 'スズメ',
                'scientific_name': 'Passer montanus',
                'category': 'bird'
            },
            {
                'species': 'Corvus macrorhynchos', 
                'common_name': 'ハシブトガラス',
                'scientific_name': 'Corvus macrorhynchos',
                'category': 'bird'
            },
            {
                'species': 'Turdus naumanni',
                'common_name': 'ツグミ',
                'scientific_name': 'Turdus naumanni', 
                'category': 'bird'
            },
            {
                'species': 'Ardea cinerea',
                'common_name': 'アオサギ',
                'scientific_name': 'Ardea cinerea',
                'category': 'bird'
            },
            {
                'species': 'Buteo buteo',
                'common_name': 'ノスリ',
                'scientific_name': 'Buteo buteo',
                'category': 'bird'
            },
            {
                'species': 'Macaca fuscata',
                'common_name': 'ニホンザル',
                'scientific_name': 'Macaca fuscata',
                'category': 'mammal'
            },
            {
                'species': 'Cervus nippon',
                'common_name': 'ニホンジカ',
                'scientific_name': 'Cervus nippon',
                'category': 'mammal'
            },
            {
                'species': 'Sus scrofa',
                'common_name': 'イノシシ',
                'scientific_name': 'Sus scrofa',
                'category': 'mammal'
            },
            {
                'species': 'Nyctereutes procyonoides',
                'common_name': 'タヌキ',
                'scientific_name': 'Nyctereutes procyonoides',
                'category': 'mammal'
            },
            {
                'species': 'Vulpes vulpes',
                'common_name': 'キツネ',
                'scientific_name': 'Vulpes vulpes',
                'category': 'mammal'
            }
        ]
        
        logging.info("MockSpeciesNet が初期化されました")
    
    def predict(self, image: np.ndarray) -> Dict[str, Any]:
        """画像の予測を実行（モックアップ）"""
        # 実際の処理をシミュレート
        time.sleep(random.uniform(0.5, 2.0))  # 処理時間のシミュレート
        
        # ランダムに検出結果を生成
        detections = []
        
        # 30%の確率で検出なし
        if random.random() < 0.3:
            return {'detections': []}
        
        # 1-3個の検出結果をランダム生成
        num_detections = random.randint(1, 3)
        
        for _ in range(num_detections):
            species_data = random.choice(self.japanese_species)
            
            detection = {
                'species': species_data['species'],
                'common_name': species_data['common_name'],
                'scientific_name': species_data['scientific_name'],
                'confidence': random.uniform(0.1, 0.95),
                'category': species_data['category'],
                'bbox': [
                    random.randint(0, 100),     # x1
                    random.randint(0, 100),     # y1
                    random.randint(200, 400),   # x2
                    random.randint(200, 400)    # y2
                ]
            }
            detections.append(detection)
        
        return {'detections': detections}

class SpeciesDetector:
    """SpeciesNet検出器クラス"""
    
    def __init__(self, config=None):
        self.config = config
        self.model = None
        self.is_initialized = False
        self.error_message = ""
        self.use_mock = not SPECIESNET_AVAILABLE
        
        # ログ設定
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        if self.use_mock:
            self.logger.info("モックアップモードで動作します")
        else:
            self.logger.info("SpeciesNet実装モードで動作します")
        
    def initialize(self) -> bool:
        """SpeciesNetモデルを初期化"""
        try:
            self.logger.info("モデルを初期化中...")
            
            if self.use_mock:
                # モックアップモードの初期化
                self.model = MockSpeciesNet()
                self.logger.info("MockSpeciesNet の初期化が完了しました")
            else:
                # 実際のSpeciesNetの初期化
                self.logger.info("SpeciesNetモデルを初期化中...")
                self.model = SpeciesNet('kaggle:google/speciesnet/pyTorch/v4.0.1a')
                self.logger.info("SpeciesNet の初期化が完了しました")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.error_message = f"モデル初期化エラー: {str(e)}"
            self.logger.error(self.error_message)
            return False
    
    def detect_single_image(self, image_path: str) -> DetectionResult:
        """単一画像の検出処理"""
        if not self.is_initialized:
            if not self.initialize():
                return DetectionResult(image_path, [])
        
        try:
            if self.use_mock:
                # モックアップモードでの処理
                image = self._load_and_preprocess_image(image_path)
                if image is None:
                    return DetectionResult(image_path, [])
                
                results = self.model.predict(image)
                detections = self._process_predictions(results)
            else:
                # 実際のSpeciesNetでの処理
                detections = self._detect_with_speciesnet(image_path)
            
            return DetectionResult(image_path, detections)
            
        except Exception as e:
            self.logger.error(f"画像 {image_path} の検出中にエラー: {str(e)}")
            return DetectionResult(image_path, [])
    
    def detect_batch(self, image_paths: List[str], 
                    progress_callback=None) -> List[DetectionResult]:
        """バッチ処理での検出"""
        if not self.is_initialized:
            if not self.initialize():
                return []
        
        results = []
        total_images = len(image_paths)
        
        try:
            batch_size = getattr(self.config, 'batch_size', 32) if self.config else 32
            
            for i in range(0, total_images, batch_size):
                batch_paths = image_paths[i:i + batch_size]
                batch_results = []
                
                # バッチ内の各画像を処理
                for j, image_path in enumerate(batch_paths):
                    result = self.detect_single_image(image_path)
                    batch_results.append(result)
                    
                    # 進捗コールバック
                    if progress_callback:
                        progress = ((i + j + 1) / total_images) * 100
                        progress_callback(progress, image_path)
                
                results.extend(batch_results)
                
                # メモリ使用量の監視と最適化
                self._manage_memory()
            
            return results
            
        except Exception as e:
            self.logger.error(f"バッチ処理中にエラー: {str(e)}")
            return results
    
    def _load_and_preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """画像の読み込みと前処理"""
        try:
            # PIL Imageで読み込み
            with Image.open(image_path) as img:
                # RGBに変換
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # サイズ制限の適用
                if self.config and hasattr(self.config, 'max_image_size'):
                    max_size = self.config.max_image_size
                    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # NumPy配列に変換
                return np.array(img)
                
        except Exception as e:
            self.logger.error(f"画像読み込みエラー {image_path}: {str(e)}")
            return None
    
    def _process_predictions(self, raw_results) -> List[Dict[str, Any]]:
        """予測結果の後処理"""
        try:
            detections = []
            confidence_threshold = getattr(self.config, 'confidence_threshold', 0.1) if self.config else 0.1
            
            # 結果形式の処理
            if isinstance(raw_results, dict):
                for detection in raw_results.get('detections', []):
                    confidence = detection.get('confidence', 0)
                    
                    if confidence >= confidence_threshold:
                        processed_detection = {
                            'species': detection.get('species', 'Unknown'),
                            'common_name': detection.get('common_name', ''),
                            'scientific_name': detection.get('scientific_name', ''),
                            'confidence': confidence,
                            'bbox': detection.get('bbox', []),
                            'category': detection.get('category', '')
                        }
                        detections.append(processed_detection)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"予測結果の処理エラー: {str(e)}")
            return []
    
    def _detect_with_speciesnet(self, image_path: str) -> List[Dict[str, Any]]:
        """SpeciesNetを使用した実際の検出処理"""
        try:
            self.logger.info(f"SpeciesNetで検出実行: {image_path}")
            
            # SpeciesNetのpredict APIを呼び出し
            results = self.model.predict(
                filepaths=[image_path],
                country='JPN',  # 日本での検出
                run_mode='single_thread',
                progress_bars=False
            )
            
            self.logger.info(f"SpeciesNet結果: {results}")
            self.logger.info(f"結果のタイプ: {type(results)}")
            
            # 結果の詳細ログ
            if isinstance(results, dict):
                self.logger.info(f"結果のキー: {results.keys()}")
            elif isinstance(results, list):
                self.logger.info(f"結果リストの長さ: {len(results)}")
                if results:
                    self.logger.info(f"最初の要素: {results[0]}")
            
            # 結果の変換処理
            detections = self._convert_speciesnet_results(results)
            
            self.logger.info(f"変換後の検出結果: {len(detections)}個")
            
            return detections
            
        except Exception as e:
            self.logger.error(f"SpeciesNet検出エラー: {str(e)}")
            import traceback
            self.logger.error(f"詳細エラー: {traceback.format_exc()}")
            return []
    
    def _convert_speciesnet_results(self, results) -> List[Dict[str, Any]]:
        """SpeciesNetの結果を標準形式に変換"""
        try:
            detections = []
            confidence_threshold = getattr(self.config, 'confidence_threshold', 0.1) if self.config else 0.1
            
            self.logger.info(f"結果変換開始 - 閾値: {confidence_threshold}")
            
            # SpeciesNet結果の構造を処理
            if isinstance(results, dict) and 'predictions' in results:
                predictions_list = results['predictions']
                
                if predictions_list and len(predictions_list) > 0:
                    prediction_data = predictions_list[0]  # 最初の画像の結果
                    
                    # メイン予測結果の処理
                    if 'prediction' in prediction_data and 'prediction_score' in prediction_data:
                        main_prediction = prediction_data['prediction']
                        main_score = prediction_data['prediction_score']
                        
                        self.logger.info(f"メイン予測: {main_prediction} (信頼度: {main_score})")
                        
                        if main_score >= confidence_threshold:
                            # メイン予測結果を追加
                            species_name = self._extract_species_name(main_prediction)
                            detection = self._create_detection_from_species(species_name, main_score)
                            if detection:
                                detections.append(detection)
                    
                    # 分類結果の処理（追加の候補）
                    if 'classifications' in prediction_data:
                        classifications = prediction_data['classifications']
                        
                        if 'classes' in classifications and 'scores' in classifications:
                            classes = classifications['classes']
                            scores = classifications['scores']
                            
                            self.logger.info(f"分類候補数: {len(classes)}")
                            
                            # 既にメイン予測を追加している場合は、2番目以降の候補を追加
                            start_index = 1 if detections else 0
                            
                            for i in range(start_index, min(len(classes), len(scores))):
                                class_name = classes[i]
                                score = scores[i]
                                
                                self.logger.info(f"  候補{i+1}: {class_name} (信頼度: {score})")
                                
                                if score >= confidence_threshold:
                                    species_name = self._extract_species_name(class_name)
                                    detection = self._create_detection_from_species(species_name, score)
                                    if detection:
                                        detections.append(detection)
            
            self.logger.info(f"変換完了: {len(detections)}個の検出結果")
            return detections
            
        except Exception as e:
            self.logger.error(f"結果変換エラー: {str(e)}")
            import traceback
            self.logger.error(f"詳細エラー: {traceback.format_exc()}")
            return []
    
    def _extract_species_name(self, speciesnet_string: str) -> str:
        """
        SpeciesNetの結果文字列から種名を抽出
        形式: 'UUID;kingdom;order;family;genus;species;common_name'
        """
        try:
            parts = speciesnet_string.split(';')
            
            if len(parts) >= 7:
                # 最後の部分（common name）を使用
                common_name = parts[-1].strip()
                
                # genus + speciesを組み合わせて学名を作成
                genus = parts[4].strip() if len(parts) > 4 and parts[4].strip() else ''
                species = parts[5].strip() if len(parts) > 5 and parts[5].strip() else ''
                
                if genus and species:
                    scientific_name = f"{genus.capitalize()} {species}"
                    self.logger.info(f"抽出結果: '{speciesnet_string}' -> 学名: '{scientific_name}', 一般名: '{common_name}'")
                    return scientific_name
                elif common_name:
                    self.logger.info(f"抽出結果: '{speciesnet_string}' -> 一般名: '{common_name}'")
                    return common_name
            
            # フォールバック: 元の文字列を返す
            self.logger.warning(f"種名抽出失敗: '{speciesnet_string}' - 元の文字列を使用")
            return speciesnet_string
            
        except Exception as e:
            self.logger.error(f"種名抽出エラー: {str(e)}")
            return speciesnet_string
    
    def _create_detection_from_species(self, species_name: str, confidence: float) -> Optional[Dict[str, Any]]:
        """種名と信頼度から検出結果を作成"""
        try:
            # 基本的な検出結果の作成
            detection = {
                'species': species_name,
                'scientific_name': species_name,
                'confidence': float(confidence),
                'category': self._get_category_from_species(species_name),
                'common_name': self._get_common_name(species_name),
                'bbox': []  # SpeciesNetは通常バウンディングボックス情報を提供しない
            }
            
            return detection
            
        except Exception as e:
            self.logger.error(f"検出結果作成エラー ({species_name}): {str(e)}")
            return None
    
    def _get_category_from_species(self, species_name: str) -> str:
        """種名からカテゴリを推定"""
        # 簡単な分類ルール（拡張版）
        bird_indicators = [
            'corvus', 'passer', 'turdus', 'ardea', 'buteo', 'falco', 'accipiter',
            'egretta',  # コサギ属
            'bubulcus',  # アマサギ属
            'aves',  # 鳥綱
            'bird', 'egret', 'heron', 'crow', 'sparrow'  # 英語名
        ]
        
        mammal_indicators = [
            'macaca', 'cervus', 'sus', 'nyctereutes', 'vulpes', 'ursus',
            'mammalia'  # 哺乳綱
        ]
        
        species_lower = species_name.lower()
        
        for indicator in bird_indicators:
            if indicator in species_lower:
                return 'bird'
        
        for indicator in mammal_indicators:
            if indicator in species_lower:
                return 'mammal'
        
        return 'unknown'
    
    def _get_common_name(self, species_name: str) -> str:
        """種名から一般名を取得（シンプル版）"""
        # シンプルに学名をそのまま返す
        return species_name
    
    def _manage_memory(self):
        """メモリ管理の最適化"""
        try:
            import gc
            gc.collect()
            
            # GPU メモリクリア（PyTorch使用時）
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
                
        except Exception as e:
            self.logger.warning(f"メモリ管理警告: {str(e)}")
    
    def get_supported_species(self) -> List[str]:
        """サポートされている種のリストを取得"""
        if not self.is_initialized:
            return []
        
        try:
            if self.use_mock:
                return [species['species'] for species in self.model.japanese_species]
            else:
                # 実際のSpeciesNetからサポート種リストを取得
                return getattr(self.model, 'supported_species', [])
        except Exception:
            return []
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.model:
            try:
                # モデルのクリーンアップ
                del self.model
                self.model = None
                self._manage_memory()
            except Exception as e:
                self.logger.warning(f"クリーンアップ警告: {str(e)}")
        
        self.is_initialized = False
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        return {
            'mode': 'mock' if self.use_mock else 'real',
            'species_net_available': SPECIESNET_AVAILABLE,
            'initialized': self.is_initialized,
            'supported_species_count': len(self.get_supported_species())
        }
