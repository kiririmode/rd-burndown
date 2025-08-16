"""プロジェクトCLIコマンドのテスト"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from rd_burndown.cli.project import project
from rd_burndown.core.models import RedmineProject


class TestProjectCommands:
    """プロジェクトコマンドのテスト"""

    def test_project_group_help(self):
        """プロジェクトグループのヘルプテスト"""
        runner = CliRunner()
        result = runner.invoke(project, ["--help"])
        assert result.exit_code == 0
        assert "プロジェクト管理コマンド" in result.output

    @patch("rd_burndown.cli.project.get_redmine_client")
    def test_project_list_table_format(self, mock_get_client):
        """プロジェクト一覧テーブル形式のテスト"""
        mock_client = Mock()
        mock_client.get_projects.return_value = [
            {"id": 1, "name": "テストプロジェクト", "identifier": "test", "status": 1}
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(project, ["list"], obj={"verbose": False})
        assert result.exit_code == 0

    @patch("rd_burndown.cli.project.get_redmine_client")
    def test_project_list_json_format(self, mock_get_client):
        """プロジェクト一覧JSON形式のテスト"""
        mock_client = Mock()
        mock_client.get_projects.return_value = [
            {"id": 1, "name": "テストプロジェクト", "identifier": "test", "status": 1}
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(
            project, ["list", "--format", "json"], obj={"verbose": False}
        )
        assert result.exit_code == 0

    @patch("rd_burndown.cli.project.get_redmine_client")
    def test_project_list_error(self, mock_get_client):
        """プロジェクト一覧取得エラーのテスト"""
        mock_client = Mock()
        mock_client.get_projects.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(project, ["list"], obj={"verbose": False})
        assert result.exit_code == 1

    @patch("rd_burndown.cli.project.get_redmine_client")
    @patch("rd_burndown.cli.project.get_data_manager")
    def test_project_info(self, mock_get_manager, mock_get_client):
        """プロジェクト詳細表示のテスト"""
        mock_client = Mock()
        project_data = RedmineProject(
            id=1,
            name="テストプロジェクト",
            identifier="test",
            description="テスト説明",
            status=1,
            created_on=datetime(2024, 1, 1),
            updated_on=datetime(2024, 1, 1),
            start_date=None,
            end_date=None,
            versions=[],
            custom_fields={},
        )
        mock_client.get_project_data.return_value = project_data
        mock_get_client.return_value = mock_client
        
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(project, ["info", "1"], obj={"verbose": False})
        if result.exit_code != 0:
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")
        assert result.exit_code == 0

    @patch("rd_burndown.cli.project.get_redmine_client")
    @patch("rd_burndown.cli.project.get_data_manager")
    def test_project_info_error(self, mock_get_manager, mock_get_client):
        """プロジェクト詳細表示エラーのテスト"""
        mock_client = Mock()
        mock_client.get_project_data.side_effect = Exception("Project not found")
        mock_get_client.return_value = mock_client
        
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(project, ["info", "1"], obj={"verbose": False})
        assert result.exit_code == 1

    @patch("rd_burndown.cli.project.get_data_manager")
    def test_project_sync(self, mock_get_manager):
        """プロジェクト同期のテスト"""
        mock_manager = Mock()
        mock_manager.sync_project.return_value = None
        mock_manager.get_cache_status.return_value = {"error": "none"}
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(project, ["sync", "1"], obj={"verbose": False})
        assert result.exit_code == 0

    @patch("rd_burndown.cli.project.get_data_manager")
    def test_project_sync_error(self, mock_get_manager):
        """プロジェクト同期エラーのテスト"""
        mock_manager = Mock()
        mock_manager.sync_project.side_effect = Exception("Sync failed")
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(project, ["sync", "1"], obj={"verbose": False})
        # ClickExceptionが発生するので終了コードは1
        assert result.exit_code == 1


def add_project_commands(cli_group):
    """プロジェクトコマンドをCLIに追加"""
    cli_group.add_command(project)