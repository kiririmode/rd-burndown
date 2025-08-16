"""設定管理システムのテスト"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from rd_burndown.utils.config import (
    ChartColors,
    Config,
    ConfigManager,
    OutputConfig,
    RedmineConfig,
    get_config_manager,
)


class TestRedmineConfig:
    """RedmineConfig のテスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        config = RedmineConfig()
        assert config.url == "http://localhost:3000"
        assert config.api_key == ""
        assert config.timeout == 30
        assert config.verify_ssl is True

    def test_custom_values(self):
        """カスタム値のテスト"""
        config = RedmineConfig(
            url="https://redmine.example.com",
            api_key="test-api-key",  # pragma: allowlist secret
            timeout=60,
            verify_ssl=False,
        )
        assert config.url == "https://redmine.example.com"
        assert config.api_key == "test-api-key"  # pragma: allowlist secret
        assert config.timeout == 60
        assert config.verify_ssl is False


class TestOutputConfig:
    """OutputConfig のテスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        config = OutputConfig()
        assert config.default_format == "png"
        assert config.default_width == 1200
        assert config.default_height == 800
        assert config.default_dpi == 300
        assert config.output_dir == "./output"


class TestChartColors:
    """ChartColors のテスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        colors = ChartColors()
        assert colors.ideal == "#2E8B57"
        assert colors.actual == "#DC143C"
        assert colors.scope == "#4169E1"
        assert colors.dynamic_ideal == "#FF8C00"
        assert colors.background == "#FFFFFF"
        assert colors.grid == "#E0E0E0"


class TestConfig:
    """Config のテスト"""

    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = Config()

        # 各セクションが正しく初期化されているか確認
        assert isinstance(config.redmine, RedmineConfig)
        assert isinstance(config.output, OutputConfig)
        assert isinstance(config.chart.colors, ChartColors)

        # デフォルト値の確認
        assert config.redmine.url == "http://localhost:3000"
        assert config.output.default_format == "png"
        assert config.chart.font_family == "DejaVu Sans"

    def test_model_dump(self):
        """model_dump のテスト"""
        config = Config()
        data = config.model_dump()

        assert "redmine" in data
        assert "output" in data
        assert "chart" in data
        assert "data" in data
        assert "date" in data
        assert "logging" in data

        # ネストした構造の確認
        assert "colors" in data["chart"]
        assert "line_styles" in data["chart"]


class TestConfigManager:
    """ConfigManager のテスト"""

    def test_init_with_default_path(self):
        """デフォルトパスでの初期化テスト"""
        manager = ConfigManager()
        expected_path = Path.home() / ".rd-burndown" / "config.yaml"
        assert manager.config_path == expected_path

    def test_init_with_custom_path(self):
        """カスタムパスでの初期化テスト"""
        custom_path = Path("/tmp/test-config.yaml")
        manager = ConfigManager(custom_path)
        assert manager.config_path == custom_path

    def test_create_default_config(self):
        """デフォルト設定作成のテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            manager = ConfigManager(config_path)

            config = manager.create_default_config()

            # ファイルが作成されているか確認
            assert config_path.exists()

            # 設定内容の確認
            assert isinstance(config, Config)
            assert config.redmine.url == "http://localhost:3000"

    def test_load_config_from_file(self):
        """ファイルからの設定読み込みテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"

            # テスト用YAML作成
            test_config = {
                "redmine": {
                    "url": "https://test.example.com",
                    "api_key": "test-key",  # pragma: allowlist secret
                    "timeout": 45,
                },
                "output": {
                    "default_format": "svg",
                    "default_width": 1600,
                },
            }

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(test_config, f)

            # 設定読み込み
            manager = ConfigManager(config_path)
            config = manager.load_config()

            # 読み込まれた設定の確認
            assert config.redmine.url == "https://test.example.com"
            assert config.redmine.api_key == "test-key"  # pragma: allowlist secret
            assert config.redmine.timeout == 45
            assert config.output.default_format == "svg"
            assert config.output.default_width == 1600

    def test_load_config_nonexistent_file(self):
        """存在しないファイルからの読み込みテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "nonexistent.yaml"
            manager = ConfigManager(config_path)

            # デフォルト設定が返されるか確認
            config = manager.load_config()
            assert isinstance(config, Config)
            assert config.redmine.url == "http://localhost:3000"

    @patch.dict(
        os.environ,
        {
            "RD_REDMINE_URL": "http://env.example.com",
            "RD_REDMINE_API_KEY": "env-api-key",  # pragma: allowlist secret
            "RD_OUTPUT_DIR": "/tmp/output",
            "RD_CACHE_TTL_HOURS": "24",
        },
    )
    def test_env_overrides(self):
        """環境変数オーバーライドのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            manager = ConfigManager(config_path)

            config = manager.load_config()

            # 環境変数で上書きされているか確認
            assert config.redmine.url == "http://env.example.com"
            assert config.redmine.api_key == "env-api-key"  # pragma: allowlist secret
            assert config.output.output_dir == "/tmp/output"
            assert config.data.cache_ttl_hours == 24

    @patch.dict(os.environ, {"RD_CACHE_TTL_HOURS": "invalid"})
    def test_env_override_invalid_int(self):
        """無効な整数値の環境変数テスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            manager = ConfigManager(config_path)

            config = manager.load_config()

            # 無効な値は無視され、デフォルト値が使用される
            assert config.data.cache_ttl_hours == 1

    def test_save_config(self):
        """設定保存のテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            manager = ConfigManager(config_path)

            # カスタム設定を作成
            config = Config()
            config.redmine.url = "https://saved.example.com"
            config.redmine.api_key = "saved-key"  # pragma: allowlist secret

            # 設定保存
            manager.save_config(config)

            # ファイルが作成されているか確認
            assert config_path.exists()

            # ファイル内容の確認
            with open(config_path, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["redmine"]["url"] == "https://saved.example.com"
            # pragma: allowlist secret
            assert saved_data["redmine"]["api_key"] == "saved-key"

    def test_config_caching(self):
        """設定キャッシュのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"
            manager = ConfigManager(config_path)

            # 初回読み込み
            config1 = manager.load_config()

            # 2回目読み込み（キャッシュされているはず）
            config2 = manager.load_config()

            # 同じインスタンスが返されるか確認
            assert config1 is config2


class TestGetConfigManager:
    """get_config_manager関数のテスト"""

    def test_default_path(self):
        """デフォルトパスでの取得テスト"""
        manager = get_config_manager()
        expected_path = Path.home() / ".rd-burndown" / "config.yaml"
        assert manager.config_path == expected_path

    def test_custom_path(self):
        """カスタムパスでの取得テスト"""
        custom_path = Path("/tmp/custom-config.yaml")
        manager = get_config_manager(custom_path)
        assert manager.config_path == custom_path


class TestIntegration:
    """統合テスト"""

    def test_full_config_workflow(self):
        """完全な設定ワークフローのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"

            # 1. ConfigManager作成
            manager = ConfigManager(config_path)

            # 2. デフォルト設定作成
            config = manager.create_default_config()
            assert config_path.exists()

            # 3. 設定変更
            config.redmine.url = "https://modified.example.com"
            config.output.default_width = 1920

            # 4. 設定保存
            manager.save_config(config)

            # 5. 新しいManagerで読み込み
            new_manager = ConfigManager(config_path)
            loaded_config = new_manager.load_config()

            # 6. 変更内容の確認
            assert loaded_config.redmine.url == "https://modified.example.com"
            assert loaded_config.output.default_width == 1920

    @patch.dict(
        os.environ,
        {
            "RD_REDMINE_URL": "http://env-override.com",
            "RD_OUTPUT_FORMAT": "svg",
        },
    )
    def test_config_with_env_and_file(self):
        """ファイル設定と環境変数の組み合わせテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"

            # ファイル設定作成
            file_config = {
                "redmine": {
                    "url": "http://file.example.com",
                    "api_key": "file-key",  # pragma: allowlist secret
                },
                "output": {
                    "default_format": "png",
                    "default_width": 1200,
                },
            }

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(file_config, f)

            # 設定読み込み
            manager = ConfigManager(config_path)
            config = manager.load_config()

            # 環境変数が優先されているか確認
            assert config.redmine.url == "http://env-override.com"  # 環境変数
            # pragma: allowlist secret
            assert config.redmine.api_key == "file-key"  # ファイル
            assert config.output.default_format == "svg"  # 環境変数
            assert config.output.default_width == 1200  # ファイル
