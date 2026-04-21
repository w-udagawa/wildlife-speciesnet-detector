"""SpeciesDetectorDirect の予測文字列パースとユーティリティのテスト

speciesnet パッケージは重量級 ML ライブラリのため、初期化を伴わない
純粋な文字列パース関数・DetectionResult の公開 API のみを検証する。
"""
import pytest

from core.species_detector_direct import DetectionResult, SpeciesDetectorDirect


@pytest.fixture
def detector():
    """モデル未初期化の検出器 (パース関数の呼び出しのみに使用)"""
    return SpeciesDetectorDirect(config=None)


class TestParsePredictionString:
    def test_full_taxonomy_string(self, detector):
        # UUID;class;order;family;genus;species;common_name
        s = "uuid-1;aves;passeriformes;corvidae;corvus;macrorhynchos;ハシブトガラス"
        result = detector._parse_prediction_string(s)
        assert result["category"] == "bird"
        # species_name は「学名 (一般名)」の併記形式
        assert result["species_name"] == "Corvus macrorhynchos (ハシブトガラス)"
        assert result["scientific_name"] == "Corvus macrorhynchos"
        assert result["common_name"] == "ハシブトガラス"

    def test_mammal_category_mapping(self, detector):
        s = "uuid-2;mammalia;carnivora;felidae;felis;catus;イエネコ"
        assert detector._parse_prediction_string(s)["category"] == "mammal"

    def test_reptile_category_mapping(self, detector):
        s = "uuid-3;reptilia;squamata;colubridae;elaphe;climacophora;アオダイショウ"
        assert detector._parse_prediction_string(s)["category"] == "reptile"

    def test_insect_category_mapping(self, detector):
        s = "uuid-4;insecta;coleoptera;scarabaeidae;trypoxylus;dichotomus;カブトムシ"
        assert detector._parse_prediction_string(s)["category"] == "insect"

    def test_unknown_class_falls_back_to_lowercase_class_name(self, detector):
        s = "uuid-arachnid;arachnida;araneae;araneidae;argiope;bruennichi;"
        # マッピングにない分類群は小文字クラス名をそのまま使う
        assert detector._parse_prediction_string(s)["category"] == "arachnida"

    def test_empty_string_returns_no_detection(self, detector):
        result = detector._parse_prediction_string("")
        assert result["species_name"] == ""
        assert result["category"] == "no_detection"

    def test_blank_label_is_no_detection(self, detector):
        """SpeciesNet の 'blank' 特殊ラベルは未検出扱い"""
        result = detector._parse_prediction_string("blank")
        assert result["category"] == "no_detection"
        assert result["species_name"] == ""

    def test_no_cv_result_label_is_no_detection(self, detector):
        result = detector._parse_prediction_string("no cv result")
        assert result["category"] == "no_detection"
        assert result["species_name"] == ""

    def test_malformed_string_does_not_raise(self, detector):
        result = detector._parse_prediction_string("not;enough;parts")
        assert isinstance(result, dict)
        assert "species_name" in result

    def test_missing_genus_uses_common_name(self, detector):
        s = "uuid-5;aves;passeriformes;corvidae;;;カラス類"
        result = detector._parse_prediction_string(s)
        assert result["species_name"] == "カラス類"


class TestExtractBbox:
    def test_returns_highest_confidence_bbox(self, detector):
        detections = [
            {"conf": 0.3, "bbox": [0.1, 0.1, 0.2, 0.2]},
            {"conf": 0.9, "bbox": [0.5, 0.5, 0.6, 0.6]},
            {"conf": 0.5, "bbox": [0.2, 0.2, 0.3, 0.3]},
        ]
        assert detector._extract_bbox_from_detections(detections) == [0.5, 0.5, 0.6, 0.6]

    def test_empty_list_returns_empty(self, detector):
        assert detector._extract_bbox_from_detections([]) == []


class TestDetectionResult:
    def test_empty_detections(self):
        result = DetectionResult("/tmp/a.jpg", [])
        assert not result.has_detections()
        assert result.get_best_detection() is None
        assert result.get_species_count() == 0

    def test_best_detection_picks_highest_confidence(self):
        detections = [
            {"species": "A", "confidence": 0.4},
            {"species": "B", "confidence": 0.9},
            {"species": "C", "confidence": 0.6},
        ]
        result = DetectionResult("/tmp/a.jpg", detections)
        assert result.has_detections()
        assert result.get_best_detection()["species"] == "B"
        assert result.get_species_count() == 3

    def test_unique_species_count(self):
        detections = [
            {"species": "A", "confidence": 0.4},
            {"species": "A", "confidence": 0.5},
            {"species": "B", "confidence": 0.6},
        ]
        assert DetectionResult("/tmp/a.jpg", detections).get_species_count() == 2
