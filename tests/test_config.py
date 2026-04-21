"""AppConfig / ConfigManager のユニットテスト"""
import json
from pathlib import Path

import pytest

from core.config import AppConfig, ConfigManager


class TestAppConfig:
    def test_defaults(self):
        config = AppConfig.get_default()
        assert 0.0 <= config.confidence_threshold <= 1.0
        assert config.batch_size > 0
        assert config.predict_chunk_size > 0
        assert config.country_filter == "JPN"

    def test_to_dict_roundtrip(self):
        config = AppConfig(confidence_threshold=0.25, batch_size=16)
        restored = AppConfig.from_dict(config.to_dict())
        assert restored.confidence_threshold == 0.25
        assert restored.batch_size == 16

    def test_from_dict_ignores_unknown_keys(self):
        """旧バージョンの設定ファイル互換性のため未知キーを無視"""
        data = {
            "confidence_threshold": 0.5,
            "batch_size": 8,
            "legacy_field_that_no_longer_exists": "whatever",
            "another_removed_setting": 42,
        }
        config = AppConfig.from_dict(data)
        assert config.confidence_threshold == 0.5
        assert config.batch_size == 8

    def test_from_dict_partial(self):
        """部分的なデータでもデフォルト値で埋まる"""
        config = AppConfig.from_dict({"batch_size": 64})
        assert config.batch_size == 64
        assert config.confidence_threshold == AppConfig.get_default().confidence_threshold


class TestConfigManager:
    def test_load_returns_default_when_no_file(self, tmp_path: Path):
        manager = ConfigManager(config_dir=tmp_path)
        config = manager.load_config()
        assert isinstance(config, AppConfig)
        assert config.confidence_threshold == AppConfig.get_default().confidence_threshold

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        manager = ConfigManager(config_dir=tmp_path)
        original = AppConfig(confidence_threshold=0.42, batch_size=24)

        assert manager.save_config(original) is True
        loaded = manager.load_config()

        assert loaded.confidence_threshold == 0.42
        assert loaded.batch_size == 24

    def test_load_recovers_from_corrupted_file(self, tmp_path: Path):
        manager = ConfigManager(config_dir=tmp_path)
        manager.config_file.write_text("{ this is not valid json", encoding="utf-8")

        config = manager.load_config()
        assert config.confidence_threshold == AppConfig.get_default().confidence_threshold

    def test_reset_writes_defaults(self, tmp_path: Path):
        manager = ConfigManager(config_dir=tmp_path)
        manager.save_config(AppConfig(confidence_threshold=0.9))

        reset = manager.reset_config()
        assert reset.confidence_threshold == AppConfig.get_default().confidence_threshold

        with open(manager.config_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["confidence_threshold"] == AppConfig.get_default().confidence_threshold
