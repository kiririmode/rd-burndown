"""CLIのテスト"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from rd_burndown.cli.main import cli, config
from rd_burndown.utils.config import Config


class TestCLIMain:
    """メインCLIのテスト"""

    def test_cli_help(self):
        """CLIヘルプのテスト"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Redmine バーンダウンチャート生成ツール" in result.output
        assert "project" in result.output
        assert "chart" in result.output
        assert "data" in result.output
        assert "config" in result.output

    def test_cli_version(self):
        """CLIバージョンのテスト"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_verbose_option(self):
        """詳細出力オプションのテスト"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--help"])

        assert result.exit_code == 0

    def test_cli_custom_config_path(self):
        """カスタム設定パスのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "custom-config.yaml"
            config_path.write_text("redmine:\n  url: http://custom.example.com\n")

            runner = CliRunner()
            result = runner.invoke(cli, ["--config", str(config_path), "--help"])

            assert result.exit_code == 0

    def test_subcommand_groups(self):
        """サブコマンドグループのテスト"""
        runner = CliRunner()

        # 各サブコマンドグループのヘルプが表示できるかテスト
        for subcommand in ["project", "chart", "data", "config"]:
            result = runner.invoke(cli, [subcommand, "--help"])
            assert result.exit_code == 0


class TestConfigCommands:
    """configサブコマンドのテスト"""

    def test_config_help(self):
        """config ヘルプのテスト"""
        runner = CliRunner()
        result = runner.invoke(config, ["--help"])

        assert result.exit_code == 0
        assert "設定管理コマンド" in result.output
        assert "init" in result.output
        assert "show" in result.output

    def test_config_init_default(self):
        """config init デフォルトのテスト"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.yaml"

            with patch("rd_burndown.cli.main.get_config_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.config_path = config_path
                mock_manager.create_default_config.return_value = Config()
                mock_get_manager.return_value = mock_manager

                runner = CliRunner()
                result = runner.invoke(cli, ["config", "init"])

                assert result.exit_code == 0
                assert "デフォルト設定ファイルを作成しました" in result.output
                mock_manager.create_default_config.assert_called_once()

    def test_config_show_table_format(self):
        """config show テーブル形式のテスト"""
        with patch("rd_burndown.cli.main.get_config_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_config = Config()
            mock_config.redmine.url = "http://test.example.com"
            mock_config.redmine.api_key = "test-key-12345"  # pragma: allowlist secret
            mock_manager.get_config.return_value = mock_config
            mock_get_manager.return_value = mock_manager

            runner = CliRunner()
            result = runner.invoke(cli, ["config", "show"])

            assert result.exit_code == 0
            assert "現在の設定" in result.output
            assert "http://test.example.com" in result.output
            assert "****2345" in result.output  # APIキーマスキング確認

    def test_config_show_json_format(self):
        """config show JSON形式のテスト"""
        with patch("rd_burndown.cli.main.get_config_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_config = Config()
            mock_manager.get_config.return_value = mock_config
            mock_get_manager.return_value = mock_manager

            runner = CliRunner()
            result = runner.invoke(cli, ["config", "show", "--format", "json"])

            assert result.exit_code == 0
            # JSON形式で出力されているか確認
            assert '"redmine"' in result.output
            assert '"output"' in result.output

    def test_main_function_with_help(self):
        """main関数のhelpテスト"""
        import sys
        from unittest.mock import patch

        from rd_burndown.cli.main import main

        # main関数が例外なく実行されることを確認
        with (
            patch.object(sys, "argv", ["rd-burndown", "--help"]),
            pytest.raises(SystemExit),
        ):  # --helpはSystemExitを発生させる
            main()

    def test_subcommand_groups(self):
        """サブコマンドグループのテスト"""
        runner = CliRunner()

        # project コマンドグループ
        result = runner.invoke(cli, ["project", "--help"])
        assert result.exit_code == 0
        assert "プロジェクト管理コマンド" in result.output

        # chart コマンドグループ
        result = runner.invoke(cli, ["chart", "--help"])
        assert result.exit_code == 0
        assert "チャート生成コマンド" in result.output

        # data コマンドグループ
        result = runner.invoke(cli, ["data", "--help"])
        assert result.exit_code == 0
        assert "データ管理コマンド" in result.output


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_keyboard_interrupt(self):
        """KeyboardInterrupt のテスト"""
        with patch("rd_burndown.cli.main.cli") as mock_cli:
            mock_cli.side_effect = KeyboardInterrupt()

            from rd_burndown.cli.main import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
