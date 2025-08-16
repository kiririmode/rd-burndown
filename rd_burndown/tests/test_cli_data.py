"""データCLIコマンドのテスト"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from rd_burndown.cli.data import data


class TestDataCommands:
    """データコマンドのテスト"""

    def test_data_group_help(self):
        """データグループのヘルプテスト"""
        runner = CliRunner()
        result = runner.invoke(data, ["--help"])
        assert result.exit_code == 0
        assert "データ管理コマンド" in result.output

    @patch("rd_burndown.cli.data.get_data_manager")
    def test_data_fetch(self, mock_get_manager):
        """データ取得のテスト"""
        mock_manager = Mock()
        mock_manager.fetch_project_updates.return_value = None
        mock_manager.get_cache_status.return_value = {"error": "none"}
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(data, ["fetch", "1"], obj={"verbose": False})
        assert result.exit_code == 0

    @patch("rd_burndown.cli.data.get_data_manager")
    def test_data_fetch_error(self, mock_get_manager):
        """データ取得エラーのテスト"""
        mock_manager = Mock()
        mock_manager.fetch_project_updates.side_effect = Exception("Fetch error")
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(data, ["fetch", "1"], obj={"verbose": False})
        assert result.exit_code == 1

    @patch("rd_burndown.cli.data.get_data_manager")
    def test_data_cache_clear(self, mock_get_manager):
        """キャッシュクリアのテスト"""
        mock_manager = Mock()
        mock_manager.clear_project_cache.return_value = None
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(data, ["cache", "clear"], obj={"verbose": False})
        assert result.exit_code == 0



def add_data_commands(cli_group):
    """データコマンドをCLIに追加"""
    cli_group.add_command(data)