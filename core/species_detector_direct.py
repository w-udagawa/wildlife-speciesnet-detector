"""
SpeciesNetネイティブAPI統合モジュール

Google SpeciesNetのPython APIを直接使用した野生生物検出機能を提供します。
モデルを1回ロードし、複数画像を真にバッチ処理します。

主要クラス:
    - DetectionResult: 検出結果を格納するデータクラス
    - SpeciesDetectorDirect: SpeciesNet検出器の実装

改善履歴:
    v1.0: 初期実装（subprocess版）
    v1.1: subprocess出力をファイルにリダイレクト（メモリ節約）
    v1.2: モックモード削除、エラーハンドリング強化
    v2.0: ネイティブAPI化 — subprocess廃止、真のバッチ処理実装
"""
import os
import gc
from typing import List, Dict, Any, Optional
from PIL import Image
import logging
from datetime import datetime
from pathlib import Path


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

class SpeciesDetectorDirect:
    """SpeciesNetネイティブAPI統合クラス"""

    def __init__(self, config=None):
        self.config = config
        self.is_initialized = False
        self.error_message = ""
        self.speciesnet_available = True
        self.model = None

        # ログ設定
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # 設定値
        self.country = getattr(config, 'country', 'JPN') if config else 'JPN'
        self.country = getattr(config, 'country_filter', self.country) if config else self.country
        self.confidence_threshold = getattr(config, 'confidence_threshold', 0.3) if config else 0.3
        self.batch_size = getattr(config, 'batch_size', 32) if config else 32
        self.run_mode = getattr(config, 'run_mode', 'multi_thread') if config else 'multi_thread'

        self.logger.info("SpeciesNetネイティブAPI統合モード")

    def initialize(self) -> bool:
        """SpeciesNetモデルを初期化"""
        try:
            self.logger.info("SpeciesNetモデルを読み込み中...")
            from speciesnet import SpeciesNet  # 遅延インポート（起動時のDLLロード回避）
            self.model = SpeciesNet(
                model_name="kaggle:google/speciesnet/pyTorch/v4.0.2a/1",
                components="all",
                geofence=True,
                multiprocessing=False
            )
            self.is_initialized = True
            self.logger.info("SpeciesNetモデル読み込み完了")
            return True
        except Exception as e:
            self.error_message = f"SpeciesNet初期化失敗: {e}"
            self.logger.error(self.error_message)
            self.speciesnet_available = False
            return False

    def predict_batch(self, image_paths: List[str]) -> List[DetectionResult]:
        """ネイティブAPIで複数画像を一括推論"""
        if not self.is_initialized:
            if not self.initialize():
                return [DetectionResult(p, []) for p in image_paths]

        try:
            predictions_data = self.model.predict(
                filepaths=image_paths,
                country=self.country,
                run_mode=self.run_mode,
                batch_size=self.batch_size,
                progress_bars=False,
                predictions_json=None
            )
        except Exception as e:
            self.logger.error(f"バッチ推論エラー: {e}")
            return [DetectionResult(p, []) for p in image_paths]

        # filepath→prediction の辞書を1回構築（O(n) lookup）
        predictions_list = predictions_data.get('predictions', [])
        pred_by_path = {}
        for prediction in predictions_list:
            abs_path = os.path.abspath(prediction.get('filepath', ''))
            pred_by_path.setdefault(abs_path, []).append(prediction)

        # O(1) lookup で結果を取得
        results = []
        for path in image_paths:
            abs_path = os.path.abspath(path)
            matched = pred_by_path.get(abs_path, [])
            detections = []
            for pred in matched:
                det = self._create_detection_from_prediction(pred)
                if det:
                    detections.append(det)
            results.append(DetectionResult(path, detections))
        return results

    def detect_single_image(self, image_path: str) -> DetectionResult:
        """単一画像の検出処理"""
        return self.predict_batch([image_path])[0]

    def _create_detection_from_prediction(self, prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """SpeciesNet予測結果から検出オブジェクトを作成"""
        try:
            prediction_str = prediction.get('prediction', '')
            prediction_score = prediction.get('prediction_score', 0)

            if prediction_score >= self.confidence_threshold:
                species_info = self._parse_prediction_string(prediction_str)

                detection = {
                    'species': species_info['species_name'],
                    'scientific_name': species_info['scientific_name'],
                    'confidence': float(prediction_score),
                    'category': species_info['category'],
                    'common_name': species_info['common_name'],
                    'bbox': self._extract_bbox_from_detections(prediction.get('detections', [])),
                    'source': prediction.get('prediction_source', 'classifier')
                }

                return detection

            return None

        except Exception as e:
            self.logger.error(f"検出オブジェクト作成エラー: {e}")
            return None

    def _parse_prediction_string(self, prediction_str: str) -> Dict[str, str]:
        """予測文字列から種情報を解析"""
        try:
            parts = prediction_str.split(';') if ';' in prediction_str else []

            result = {
                'species_name': 'Unknown',
                'scientific_name': 'Unknown',
                'category': 'unknown',
                'common_name': ''
            }

            if len(parts) >= 7:
                # UUID;class;order;family;genus;species;common_name
                class_name = parts[1].strip() if len(parts) > 1 else ''
                genus = parts[4].strip() if len(parts) > 4 else ''
                species = parts[5].strip() if len(parts) > 5 else ''
                common_name = parts[6].strip() if len(parts) > 6 else ''

                # カテゴリ決定
                if class_name == 'aves':
                    result['category'] = 'bird'
                elif class_name == 'mammalia':
                    result['category'] = 'mammal'
                elif class_name == 'reptilia':
                    result['category'] = 'reptile'
                else:
                    result['category'] = class_name or 'unknown'

                # 種名決定
                if genus and species:
                    result['species_name'] = f"{genus.capitalize()} {species}"
                    result['scientific_name'] = f"{genus.capitalize()} {species}"
                elif common_name:
                    result['species_name'] = common_name
                    result['scientific_name'] = common_name
                else:
                    result['species_name'] = prediction_str
                    result['scientific_name'] = prediction_str

                result['common_name'] = common_name

            return result

        except Exception as e:
            self.logger.error(f"予測文字列解析エラー: {e}")
            return {
                'species_name': prediction_str,
                'scientific_name': prediction_str,
                'category': 'unknown',
                'common_name': ''
            }

    def _extract_bbox_from_detections(self, detections: List[Dict[str, Any]]) -> List[float]:
        """検出結果からバウンディングボックスを抽出"""
        try:
            if detections and len(detections) > 0:
                best_detection = max(detections, key=lambda x: x.get('conf', 0))
                return best_detection.get('bbox', [])
            return []
        except Exception:
            return []

    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.model is not None:
            del self.model
            self.model = None
        self.is_initialized = False
        gc.collect()

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        return {
            'mode': 'native_speciesnet',
            'species_net_available': self.speciesnet_available,
            'initialized': self.is_initialized,
            'supported_species_count': 2000,
            'version': 'SpeciesNet Native API v2.0',
            'country': self.country,
            'confidence_threshold': self.confidence_threshold,
            'batch_size': self.batch_size,
            'run_mode': self.run_mode
        }

# 下位互換性のためのエイリアス
SpeciesDetector = SpeciesDetectorDirect
