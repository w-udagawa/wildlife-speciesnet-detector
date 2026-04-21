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

    # SpeciesNet class名 → 表示カテゴリのマッピング
    _CATEGORY_MAP = {
        'aves': 'bird',
        'mammalia': 'mammal',
        'reptilia': 'reptile',
        'amphibia': 'amphibian',
        'actinopterygii': 'fish',
        'insecta': 'insect',
    }

    # SpeciesNet が動物不在/判定不能を示す際の特殊ラベル（全て lowercase 比較）
    _NO_DETECTION_LABELS = {'blank', 'no cv result', 'no_cv_result'}

    @classmethod
    def is_no_detection_label(cls, value: str) -> bool:
        """species/common_name が「未検出」を意味する特殊値かどうか判定"""
        if not value:
            return True
        return value.strip().lower() in cls._NO_DETECTION_LABELS

    def _create_detection_from_prediction(self, prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """SpeciesNet予測結果から検出オブジェクトを作成"""
        try:
            prediction_score = prediction.get('prediction_score', 0)

            if prediction_score < self.confidence_threshold:
                return None

            # 構造化キーを優先し、無い場合のみ prediction 文字列をパース
            species_info = self._extract_species_info(prediction)

            return {
                'species': species_info['species_name'],
                'scientific_name': species_info['scientific_name'],
                'confidence': float(prediction_score),
                'category': species_info['category'],
                'common_name': species_info['common_name'],
                'bbox': self._extract_bbox_from_detections(prediction.get('detections', [])),
                'source': prediction.get('prediction_source', 'classifier')
            }

        except (KeyError, TypeError, ValueError) as e:
            self.logger.warning(f"検出オブジェクト作成をスキップ (不正な予測データ): {e}")
            return None

    def _extract_species_info(self, prediction: Dict[str, Any]) -> Dict[str, str]:
        """予測辞書から種情報を取り出す（構造化キー優先、文字列フォールバック）"""
        # 構造化キー（将来SpeciesNetが個別キーを返すようになった場合に備える）
        class_name = (prediction.get('class') or prediction.get('class_name') or '').strip()
        genus = (prediction.get('genus') or '').strip()
        species = (prediction.get('species') or '').strip()
        common_name = (prediction.get('common_name') or '').strip()

        # いずれか構造化キーがあれば、それを優先利用
        if class_name or genus or species or common_name:
            return self._build_species_info(class_name, genus, species, common_name,
                                            fallback=prediction.get('prediction', ''))

        # 文字列パース（現行のSpeciesNet仕様: UUID;class;order;family;genus;species;common_name）
        return self._parse_prediction_string(prediction.get('prediction', ''))

    def _build_species_info(self, class_name: str, genus: str, species: str,
                            common_name: str, fallback: str = '') -> Dict[str, str]:
        """分類情報から表示用の dict を組み立てる

        species_name は「学名 (一般名)」形式で、両者が同一・片方のみ存在する場合は
        重複を避ける。SpeciesNet の特殊ラベル (blank, no cv result) は未検出扱い。
        """
        category = self._CATEGORY_MAP.get(class_name.lower(), class_name.lower() or 'unknown')

        # 特殊ラベル: 分類情報のすべて（非空のもの）が blank/no cv result なら未検出扱い
        # - "uuid;;;;;;blank"            → common_name='blank' のみ → 未検出
        # - "uuid;no cv;;;no cv;no cv;no cv" → 全て no cv → 未検出
        taxo_values = [v for v in (class_name, genus, species, common_name) if v]
        if taxo_values and all(self.is_no_detection_label(v) for v in taxo_values):
            return {
                'species_name': '',
                'scientific_name': '',
                'category': 'no_detection',
                'common_name': '',
            }

        # 学名の組立
        if genus and species:
            sci_name = f"{genus.capitalize()} {species}"
        elif genus:
            sci_name = genus.capitalize()
        elif common_name and not self.is_no_detection_label(common_name):
            sci_name = common_name
        else:
            sci_name = fallback or 'Unknown'

        # 表示名: 「英語 (日本語)」形式。common_name が sci_name と同一/包含関係なら単独表示
        display_common = '' if self.is_no_detection_label(common_name) else common_name
        if display_common and display_common.lower() != sci_name.lower():
            species_name = f"{sci_name} ({display_common})"
        else:
            species_name = sci_name

        return {
            'species_name': species_name,
            'scientific_name': sci_name,
            'category': category,
            'common_name': display_common,
        }

    def _parse_prediction_string(self, prediction_str: str) -> Dict[str, str]:
        """予測文字列から種情報を解析（SpeciesNet セミコロン区切り仕様）"""
        # 特殊ラベル（blank / no cv result など）や空文字は未検出扱い
        if self.is_no_detection_label(prediction_str):
            return {
                'species_name': '',
                'scientific_name': '',
                'category': 'no_detection',
                'common_name': '',
            }

        default = {
            'species_name': prediction_str,
            'scientific_name': prediction_str,
            'category': 'unknown',
            'common_name': ''
        }

        if ';' not in prediction_str:
            return default

        parts = [p.strip() for p in prediction_str.split(';')]

        if len(parts) < 7:
            self.logger.warning(
                f"予測文字列のフィールド数が想定(7)と異なります (実際: {len(parts)}): {prediction_str!r}"
            )
            return default

        # UUID;class;order;family;genus;species;common_name
        _, class_name, _order, _family, genus, species, common_name = parts[:7]

        return self._build_species_info(class_name, genus, species, common_name,
                                        fallback=prediction_str)

    def _extract_bbox_from_detections(self, detections: List[Dict[str, Any]]) -> List[float]:
        """検出結果からバウンディングボックスを抽出"""
        if not detections:
            return []
        try:
            best_detection = max(detections, key=lambda x: x.get('conf', 0))
            return best_detection.get('bbox', [])
        except (TypeError, ValueError) as e:
            self.logger.warning(f"bbox抽出に失敗 (不正な検出データ): {e}")
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
