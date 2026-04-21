"""構造化キーを含む予測データの優先利用テスト"""
import pytest

from core.species_detector_direct import SpeciesDetectorDirect


@pytest.fixture
def detector():
    return SpeciesDetectorDirect(config=None)


class TestExtractSpeciesInfo:
    def test_prefers_structured_keys_over_string(self, detector):
        prediction = {
            'class': 'aves',
            'genus': 'Corvus',
            'species': 'macrorhynchos',
            'common_name': 'ハシブトガラス',
            'prediction': 'ignored;this;should;not;be;used;string',
        }
        info = detector._extract_species_info(prediction)
        assert info['category'] == 'bird'
        # 「英語学名 (日本語一般名)」形式で併記
        assert info['species_name'] == 'Corvus macrorhynchos (ハシブトガラス)'
        assert info['scientific_name'] == 'Corvus macrorhynchos'
        assert info['common_name'] == 'ハシブトガラス'

    def test_falls_back_to_string_when_no_structured_keys(self, detector):
        prediction = {
            'prediction': 'uuid;mammalia;carnivora;felidae;felis;catus;イエネコ',
        }
        info = detector._extract_species_info(prediction)
        assert info['category'] == 'mammal'
        assert info['species_name'] == 'Felis catus (イエネコ)'
        assert info['scientific_name'] == 'Felis catus'

    def test_no_duplication_when_common_equals_scientific(self, detector):
        """common_name と学名が同じ場合、括弧で重複表示しない"""
        prediction = {
            'prediction': 'uuid;aves;;corvidae;;;corvidae family',
        }
        info = detector._extract_species_info(prediction)
        assert info['species_name'] == 'corvidae family'
        assert '(' not in info['species_name']

    def test_handles_completely_missing_prediction(self, detector):
        info = detector._extract_species_info({})
        # 空の予測辞書は未検出として扱う
        assert info['category'] == 'no_detection'
        assert info['species_name'] == ''


class TestCreateDetectionFromPrediction:
    def test_skips_below_confidence_threshold(self, detector):
        detector.confidence_threshold = 0.5
        prediction = {
            'prediction': 'uuid;aves;x;y;corvus;corone;カラス',
            'prediction_score': 0.3,
        }
        assert detector._create_detection_from_prediction(prediction) is None

    def test_accepts_above_confidence_threshold(self, detector):
        detector.confidence_threshold = 0.1
        prediction = {
            'prediction': 'uuid;aves;x;y;corvus;corone;カラス',
            'prediction_score': 0.9,
            'detections': [],
        }
        result = detector._create_detection_from_prediction(prediction)
        assert result is not None
        assert result['confidence'] == 0.9
        assert result['category'] == 'bird'

    def test_malformed_prediction_returns_none(self, detector):
        detector.confidence_threshold = 0.1
        # prediction_score が文字列で float 化できない場合も安全に None を返す
        prediction = {
            'prediction': 'uuid;aves;x;y;genus;species;common',
            'prediction_score': 'not_a_number',
        }
        assert detector._create_detection_from_prediction(prediction) is None
