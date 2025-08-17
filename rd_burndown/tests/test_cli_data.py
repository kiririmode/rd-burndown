"""データCLIコマンドのテスト"""

from datetime import date
from unittest.mock import Mock, patch

import click
from click.testing import CliRunner

from rd_burndown.cli.data import data as data_cli


class TestDataCommands:
    """データコマンドのテスト"""

    def test_data_group_help(self):
        """データグループのヘルプテスト"""
        runner = CliRunner()
        result = runner.invoke(data_cli, ["--help"])
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
        result = runner.invoke(data_cli, ["fetch", "1"], obj={"verbose": False})
        assert result.exit_code == 0

    @patch("rd_burndown.cli.data.get_data_manager")
    def test_data_fetch_error(self, mock_get_manager):
        """データ取得エラーのテスト"""
        mock_manager = Mock()
        mock_manager.fetch_project_updates.side_effect = Exception("Fetch error")
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(data_cli, ["fetch", "1"], obj={"verbose": False})
        assert result.exit_code == 1

    @patch("rd_burndown.cli.data.get_data_manager")
    def test_data_cache_clear(self, mock_get_manager):
        """データキャッシュクリアのテスト"""
        mock_manager = Mock()
        mock_manager.clear_project_cache.return_value = None
        mock_get_manager.return_value = mock_manager

        runner = CliRunner()
        result = runner.invoke(data_cli, ["cache", "clear"], obj={"verbose": False})
        assert result.exit_code == 0


class TestDataFetchCommand:
    """Data fetch command tests."""

    def test_fetch_with_full_option(self):
        """Test fetch command with --full option."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli, ["fetch", "1", "--full"], obj={"verbose": False}
            )

            assert result.exit_code == 0
            mock_manager.fetch_project_updates.assert_called_once_with(
                project_id=1, incremental=False, since_date=None
            )

    def test_fetch_with_since_option(self):
        """Test fetch command with --since option."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli,
                ["fetch", "1", "--since", "2024-01-01"],
                obj={"verbose": False},
            )

            assert result.exit_code == 0
            mock_manager.fetch_project_updates.assert_called_once_with(
                project_id=1, incremental=True, since_date=date(2024, 1, 1)
            )

    def test_fetch_with_verbose(self):
        """Test fetch command with verbose output."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {
                "tickets_count": 10,
                "snapshots_count": 20,
                "scope_changes_count": 5,
            }
            mock_dm.return_value = mock_manager

            # Note: The -v flag and obj verbose setting interact in a complex way
            # This test focuses on the core functionality rather than CLI flag handling
            result = runner.invoke(data_cli, ["fetch", "1"], obj={"verbose": True})

            assert result.exit_code == 0
            mock_manager.get_cache_status.assert_called_once_with(1)


class TestDataCacheCommand:
    """Data cache command tests."""

    def test_cache_clear_with_project_id(self):
        """Test cache clear for specific project."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli,
                ["cache", "clear", "--project-id", "1"],
                obj={"verbose": False},
            )

            assert result.exit_code == 0
            mock_manager.clear_project_cache.assert_called_once_with(1)

    def test_cache_clear_without_project_id(self):
        """Test cache clear without project ID."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_dm.return_value = mock_manager

            result = runner.invoke(data_cli, ["cache", "clear"], obj={"verbose": False})

            assert result.exit_code == 0
            assert "プロジェクトIDを指定してください" in result.output

    def test_cache_clear_error(self):
        """Test cache clear with error."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.clear_project_cache.side_effect = Exception("Clear error")
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli,
                ["cache", "clear", "--project-id", "1"],
                obj={"verbose": False},
            )

            assert result.exit_code == 1
            # The exception type varies depending on CLI implementation

    def test_cache_status_specific_project(self):
        """Test cache status for specific project."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {
                "project_name": "Test Project",
                "tickets_count": 10,
                "snapshots_count": 20,
                "scope_changes_count": 5,
                "last_update": "2024-01-01 12:00:00",
                "database_size": 1024000,
            }
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli,
                ["cache", "status", "--project-id", "1"],
                obj={"verbose": False},
            )

            assert result.exit_code == 0
            mock_manager.get_cache_status.assert_called_once_with(1)

    def test_cache_status_project_error(self):
        """Test cache status for project with error."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {"error": "Project not found"}
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli,
                ["cache", "status", "--project-id", "1"],
                obj={"verbose": False},
            )

            assert result.exit_code == 0
            assert "Project not found" in result.output

    def test_cache_status_global(self):
        """Test cache status for all projects."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {
                "database_info": {
                    "version": "3.37.0",
                    "file_size_bytes": 2048000,
                    "tables": {
                        "projects": 5,
                        "tickets": 50,
                        "daily_snapshots": 100,
                        "scope_changes": 10,
                    },
                },
                "cache_directory": "/tmp/cache",
                "cache_ttl_hours": 24,
            }
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli, ["cache", "status"], obj={"verbose": False}
            )

            assert result.exit_code == 0
            mock_manager.get_cache_status.assert_called_once_with(None)

    def test_cache_status_global_verbose(self):
        """Test cache status for all projects with verbose."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {
                "database_info": {
                    "version": "3.37.0",
                    "file_size_bytes": 2048000,
                    "tables": {
                        "projects": 5,
                        "tickets": 50,
                        "daily_snapshots": 100,
                        "scope_changes": 10,
                    },
                },
                "cache_directory": "/tmp/cache",
                "cache_ttl_hours": 24,
            }
            mock_dm.return_value = mock_manager

            result = runner.invoke(data_cli, ["cache", "status"], obj={"verbose": True})

            assert result.exit_code == 0

    def test_cache_status_error(self):
        """Test cache status with error."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.side_effect = Exception("Status error")
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli, ["cache", "status"], obj={"verbose": False}
            )

            assert result.exit_code == 1
            # The exception type varies depending on CLI implementation

    def test_cache_size_specific_project(self):
        """Test cache size for specific project."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {"database_size": 1024000}
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli, ["cache", "size", "--project-id", "1"], obj={"verbose": False}
            )

            assert result.exit_code == 0
            mock_manager.get_cache_status.assert_called_once_with(1)

    def test_cache_size_project_error(self):
        """Test cache size for project with error."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {"error": "Project not found"}
            mock_dm.return_value = mock_manager

            result = runner.invoke(
                data_cli, ["cache", "size", "--project-id", "1"], obj={"verbose": False}
            )

            assert result.exit_code == 0
            assert "Project not found" in result.output

    def test_cache_size_global(self):
        """Test cache size for all projects."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.return_value = {
                "database_info": {"file_size_bytes": 2048000}
            }
            mock_dm.return_value = mock_manager

            result = runner.invoke(data_cli, ["cache", "size"], obj={"verbose": False})

            assert result.exit_code == 0

    def test_cache_size_error(self):
        """Test cache size with error."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_cache_status.side_effect = Exception("Size error")
            mock_dm.return_value = mock_manager

            result = runner.invoke(data_cli, ["cache", "size"], obj={"verbose": False})

            assert result.exit_code == 1
            # The exception type varies depending on CLI implementation


class TestDataExportCommand:
    """Data export command tests."""

    def test_export_json_default(self):
        """Test export command with JSON format (default)."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.return_value = {
                "project": {"id": 1, "name": "Test Project"},
                "snapshots": [{"date": "2024-01-01", "remaining_hours": 100.0}],
                "scope_changes": [],
            }
            mock_dm.return_value = mock_manager

            with (
                patch("builtins.open", create=True) as mock_open,
                patch("json.dump") as mock_json_dump,
            ):
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                result = runner.invoke(
                    data_cli, ["export", "1"], obj={"verbose": False}
                )

                assert result.exit_code == 0
                mock_manager.get_project_timeline.assert_called_once_with(1)
                mock_json_dump.assert_called_once()

    def test_export_csv_format(self):
        """Test export command with CSV format."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.return_value = {
                "project": {"id": 1, "name": "Test Project"},
                "snapshots": [{"date": "2024-01-01", "remaining_hours": 100.0}],
                "scope_changes": [],
            }
            mock_dm.return_value = mock_manager

            with (
                patch("builtins.open", create=True) as mock_open,
                patch("csv.DictWriter") as mock_csv,
            ):
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                mock_writer = Mock()
                mock_csv.return_value = mock_writer

                result = runner.invoke(
                    data_cli,
                    ["export", "1", "--format", "csv"],
                    obj={"verbose": False},
                )

                assert result.exit_code == 0
                mock_writer.writeheader.assert_called_once()
                mock_writer.writerows.assert_called_once()

    def test_export_with_output_path(self):
        """Test export command with custom output path."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.return_value = {
                "project": {"id": 1, "name": "Test Project"},
                "snapshots": [],
                "scope_changes": [],
            }
            mock_dm.return_value = mock_manager

            with (
                patch("builtins.open", create=True) as mock_open,
                patch("json.dump"),
            ):
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                result = runner.invoke(
                    data_cli,
                    ["export", "1", "--output", "custom.json"],
                    obj={"verbose": False},
                )

                assert result.exit_code == 0

    def test_export_with_date_range(self):
        """Test export command with date range filtering."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.return_value = {
                "project": {"id": 1, "name": "Test Project"},
                "snapshots": [
                    {"date": "2024-01-01", "remaining_hours": 100.0},
                    {"date": "2024-01-15", "remaining_hours": 50.0},
                    {"date": "2024-02-01", "remaining_hours": 25.0},
                ],
                "scope_changes": [{"date": "2024-01-10", "hours_delta": 10.0}],
            }
            mock_dm.return_value = mock_manager

            with (
                patch("builtins.open", create=True) as mock_open,
                patch("json.dump"),
            ):
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                result = runner.invoke(
                    data_cli,
                    ["export", "1", "--from", "2024-01-05", "--to", "2024-01-20"],
                    obj={"verbose": False},
                )

                assert result.exit_code == 0

    def test_export_with_verbose(self):
        """Test export command with verbose output."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.return_value = {
                "project": {"id": 1, "name": "Test Project"},
                "snapshots": [{"date": "2024-01-01", "remaining_hours": 100.0}],
                "scope_changes": [],
            }
            mock_dm.return_value = mock_manager

            with (
                patch("builtins.open", create=True) as mock_open,
                patch("pathlib.Path.stat") as mock_stat,
                patch("json.dump"),
            ):
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                mock_stat_obj = Mock()
                mock_stat_obj.st_size = 1024
                mock_stat.return_value = mock_stat_obj

                result = runner.invoke(data_cli, ["export", "1"], obj={"verbose": True})

                assert result.exit_code == 0

    def test_export_project_not_found(self):
        """Test export command when project not found."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.return_value = None
            mock_dm.return_value = mock_manager

            result = runner.invoke(data_cli, ["export", "999"], obj={"verbose": False})

            assert result.exit_code == 1
            # The exception type varies depending on CLI implementation

    def test_export_with_error(self):
        """Test export command with error."""
        runner = CliRunner()
        with patch("rd_burndown.cli.data.get_data_manager") as mock_dm:
            mock_manager = Mock()
            mock_manager.get_project_timeline.side_effect = Exception("Export error")
            mock_dm.return_value = mock_manager

            result = runner.invoke(data_cli, ["export", "1"], obj={"verbose": False})

            assert result.exit_code == 1
            # The exception type varies depending on CLI implementation


def test_add_data_commands():
    """Test add_data_commands function."""
    from rd_burndown.cli.data import add_data_commands

    @click.group()
    def test_cli():
        pass

    add_data_commands(test_cli)

    # Verify that the data command was added
    assert "data" in test_cli.commands
