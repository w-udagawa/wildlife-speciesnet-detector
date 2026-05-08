"""JapaneseNameTranslator のユニットテスト"""
import json
from pathlib import Path

import pytest

from utils.japanese_names import JapaneseNameTranslator, get_translator, reset_translator_for_test


@pytest.fixture(autouse=True)
def _reset_singleton():
    """各テストで Translator シングルトンをリセット"""
    reset_translator_for_test()
    yield
    reset_translator_for_test()


class TestSpeciesLookup:
    def test_exact_match_returns_japanese(self):
        t = JapaneseNameTranslator(data={
            "species": {"Corvus macrorhynchos": "ハシブトガラス"},
            "genus": {},
            "category": {},
        })
        assert t.translate_species("Corvus macrorhynchos") == "ハシブトガラス"

    def test_unknown_species_returns_empty(self):
        t = JapaneseNameTranslator(data={"species": {}, "genus": {}, "category": {}})
        assert t.translate_species("Unknown species") == ""

    def test_genus_fallback_when_species_missing(self):
        t = JapaneseNameTranslator(data={
            "species": {},
            "genus": {"Corvus": "カラス属"},
            "category": {},
        })
        # 学名 "Corvus" は genus キーにヒット
        assert t.translate_species("Corvus") == "カラス属"
        # "Corvus 不明種" のように属名が先頭にあれば genus fallback
        assert t.translate_species("Corvus unknown") == "カラス属"

    def test_empty_input_returns_empty(self):
        t = JapaneseNameTranslator(data={"species": {}, "genus": {}, "category": {}})
        assert t.translate_species("") == ""
        assert t.translate_species("   ") == ""

    def test_real_json_loaded(self):
        """同梱 JSON のシードデータが期待通り解決できる"""
        t = get_translator()
        # Phase 1 シードに含まれる種
        assert t.translate_species("Corvus macrorhynchos") == "ハシブトガラス"
        assert t.translate_species("Procyon lotor") == "アライグマ"


class TestCategoryLookup:
    def test_known_categories(self):
        t = JapaneseNameTranslator(data={
            "species": {}, "genus": {},
            "category": {"bird": "鳥類", "mammal": "哺乳類", "no_detection": "未検出"},
        })
        assert t.translate_category("bird") == "鳥類"
        assert t.translate_category("mammal") == "哺乳類"
        assert t.translate_category("no_detection") == "未検出"

    def test_unknown_category_passes_through(self):
        """未登録カテゴリはそのまま返す（'arachnida' 等の小文字classフォールバックを保護）"""
        t = JapaneseNameTranslator(data={"species": {}, "genus": {}, "category": {"bird": "鳥類"}})
        assert t.translate_category("arachnida") == "arachnida"

    def test_empty_returns_empty(self):
        t = JapaneseNameTranslator(data={"species": {}, "genus": {}, "category": {}})
        assert t.translate_category("") == ""


class TestGracefulDegrade:
    def test_missing_json_yields_empty_translator(self, tmp_path: Path, monkeypatch):
        """JSON が存在しなくても起動は止まらず、空マップで動作する"""
        from utils import japanese_names as jn

        monkeypatch.setattr(jn, "_JSON_PATH", tmp_path / "nonexistent.json")
        reset_translator_for_test()
        t = get_translator()
        assert t.translate_species("Corvus macrorhynchos") == ""
        assert t.translate_category("bird") == "bird"  # passthrough

    def test_corrupt_json_yields_empty_translator(self, tmp_path: Path, monkeypatch):
        """JSON が壊れていても起動は止まらない"""
        bad = tmp_path / "japanese_names.json"
        bad.write_text("{ this is not valid json", encoding="utf-8")

        from utils import japanese_names as jn
        monkeypatch.setattr(jn, "_JSON_PATH", bad)
        reset_translator_for_test()
        t = get_translator()
        assert t.translate_species("Corvus macrorhynchos") == ""

    def test_singleton_reuses_loaded_data(self):
        """get_translator() の複数回呼び出しで JSON ロードは1回だけ"""
        t1 = get_translator()
        t2 = get_translator()
        assert t1 is t2
