"""学名・カテゴリの和名翻訳ユーティリティ

CSV / 振り分けフォルダ名 / ピボット行ラベルなど、出力レイヤーで和名を解決するための
シンレイヤー。SpeciesNet の英語 common_name はそのまま保持し、ここでは scientific_name
（"Genus species"）→和名のマッピングを行う。

データソース: utils/japanese_names.json（手作りシード、Phase 3 で GBIF から自動生成予定）

設計:
    - JSON 未存在 / 構造不正の場合は warning を1回だけ出して空マップで動作
      （配布版で同梱漏れ等が起きてもアプリ起動は止めない）
    - 学名→和名キャッシュは JSON ロード時に1度だけ構築
    - スレッドセーフ（読み取り専用辞書）
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Optional

_logger = logging.getLogger(__name__)

_JSON_PATH = Path(__file__).parent / "japanese_names.json"


class JapaneseNameTranslator:
    """学名→和名・カテゴリ英語→日本語のルックアップ"""

    def __init__(self, data: Optional[Dict] = None):
        self._species: Dict[str, str] = {}
        self._genus: Dict[str, str] = {}
        self._category: Dict[str, str] = {}

        if data is None:
            data = self._load_json(_JSON_PATH)

        if data:
            self._species = dict(data.get("species") or {})
            self._genus = dict(data.get("genus") or {})
            self._category = dict(data.get("category") or {})

    @staticmethod
    def _load_json(path: Path) -> Optional[Dict]:
        if not path.exists():
            _logger.warning(
                "japanese_names.json が見つかりません (%s)。和名は空欄で動作します。",
                path,
            )
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            _logger.warning(
                "japanese_names.json の読み込みに失敗しました (%s): %s。和名は空欄で動作します。",
                path,
                e,
            )
            return None

    def translate_species(self, scientific_name: str) -> str:
        """学名（"Genus species" or "Genus"）から和名を取得。未登録時は空文字。

        - 完全一致を試み、なければ最初のトークン（属名）でフォールバック
        - "Corvus macrorhynchos" → "ハシブトガラス"
        - "Corvus" → "カラス属"
        """
        if not scientific_name:
            return ""
        key = scientific_name.strip()
        if not key:
            return ""

        if key in self._species:
            return self._species[key]

        # 属名フォールバック（"Genus species" の場合）
        first_token = key.split()[0] if " " in key else key
        if first_token in self._genus:
            return self._genus[first_token]

        return ""

    def translate_category(self, internal: str) -> str:
        """内部カテゴリ（bird/mammal/...）→日本語。未登録時は元の値をそのまま返す。"""
        if not internal:
            return ""
        return self._category.get(internal, internal)


_singleton: Optional[JapaneseNameTranslator] = None
_singleton_lock = threading.Lock()


def get_translator() -> JapaneseNameTranslator:
    """プロセス全体で共有する Translator を取得（最初の呼び出しで JSON ロード）"""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = JapaneseNameTranslator()
    return _singleton


def reset_translator_for_test() -> None:
    """テスト用: シングルトンをリセットして次回再ロードさせる"""
    global _singleton
    with _singleton_lock:
        _singleton = None
