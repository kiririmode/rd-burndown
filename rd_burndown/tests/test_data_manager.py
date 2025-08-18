"""Test cases for rd_burndown.core.data_manager module."""

from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest

from rd_burndown.core.data_manager import (
    DataManager,
    DataManagerError,
    get_data_manager,
)
from rd_burndown.core.models import RedmineProject, TicketData


class TestDataManagerError:
    """Test DataManagerError exception."""

    def test_data_manager_error_inherits_from_exception(self):
        """Test that DataManagerError inherits from Exception."""
        error = DataManagerError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"


class TestDataManager:
    """Test DataManager class."""

    @pytest.fixture
    def data_manager(self):
        """Create a DataManager instance with mocked dependencies."""
        with (
            patch("rd_burndown.core.data_manager.get_config_manager") as mock_get_cm,
            patch("rd_burndown.core.data_manager.get_database_manager") as mock_get_db,
            patch("rd_burndown.core.data_manager.get_redmine_client") as mock_get_rc,
        ):
            # Setup mocks
            mock_config_manager = Mock()
            mock_config = Mock()
            mock_config.data.cache_dir = "cache"
            # 完了ステータスの設定を追加
            mock_config.data.completed_statuses = ["完了", "Closed", "クローズ"]
            mock_config_manager.load_config.return_value = mock_config

            # Mock database manager with context manager support
            mock_db_manager = Mock()
            mock_connection = Mock()

            # Mock database queries for _get_project method
            mock_row = Mock()
            mock_row.keys.return_value = [
                "id",
                "name",
                "identifier",
                "start_date",
                "end_date",
            ]

            def mock_row_getitem(self, key):
                if key == "id":
                    return 1
                if key == "name":
                    return "Test Project"
                if key == "identifier":
                    return "test-project"
                if key == "start_date":
                    return "2024-01-01"
                if key == "end_date":
                    return "2024-12-31"
                return None

            mock_row.__getitem__ = mock_row_getitem

            mock_execute = Mock()
            mock_execute.fetchone.return_value = mock_row
            mock_execute.fetchall.return_value = []
            mock_connection.execute.return_value = mock_execute

            mock_db_manager.get_connection.return_value.__enter__ = Mock(
                return_value=mock_connection
            )
            mock_db_manager.get_connection.return_value.__exit__ = Mock(
                return_value=None
            )

            # Mock all database operations to prevent actual calls
            mock_db_manager.save_project = Mock()
            mock_db_manager.save_project_versions = Mock()
            mock_db_manager.save_tickets = Mock()
            mock_db_manager.get_project = Mock(
                return_value={"id": 1, "name": "Test Project"}
            )
            mock_db_manager.get_daily_snapshots = Mock(return_value=[])
            mock_db_manager.get_scope_changes = Mock(return_value=[])
            mock_db_manager.clear_project_data = Mock()
            mock_db_manager.get_cache_info = Mock(
                return_value={
                    "project_count": 1,
                    "tickets_count": 10,
                    "snapshots_count": 30,
                    "last_sync": datetime(2024, 1, 10),
                    "cache_size_mb": 1.5,
                }
            )
            mock_db_manager.get_last_update = Mock(return_value=datetime(2024, 1, 5))
            mock_db_manager.save_daily_snapshots = Mock()
            mock_db_manager.save_scope_changes = Mock()
            mock_db_manager.get_database_info = Mock(
                return_value={
                    "project_count": 1,
                    "tickets_count": 10,
                    "snapshots_count": 30,
                    "last_sync": datetime(2024, 1, 10),
                    "cache_size_mb": 1.5,
                }
            )

            mock_redmine_client = Mock()
            # Mock all redmine client methods to prevent actual API calls
            mock_redmine_client.get_project_data.return_value = None
            mock_redmine_client.get_project_versions.return_value = []
            mock_redmine_client.get_project_tickets.return_value = []
            mock_redmine_client.get_updated_tickets.return_value = []
            mock_redmine_client.get_all_project_journals.return_value = []

            mock_get_cm.return_value = mock_config_manager
            mock_get_db.return_value = mock_db_manager
            mock_get_rc.return_value = mock_redmine_client

            return DataManager()

    def test_init_success(self):
        """Test successful DataManager initialization."""
        with (
            patch("rd_burndown.core.data_manager.get_config_manager") as mock_get_cm,
            patch("rd_burndown.core.data_manager.get_database_manager") as mock_get_db,
            patch("rd_burndown.core.data_manager.get_redmine_client") as mock_get_rc,
        ):
            # Setup mocks
            mock_config_manager = Mock()
            mock_config = Mock()
            mock_config.data.cache_dir = "cache"
            mock_config_manager.load_config.return_value = mock_config

            mock_db_manager = Mock()
            mock_redmine_client = Mock()

            mock_get_cm.return_value = mock_config_manager
            mock_get_db.return_value = mock_db_manager
            mock_get_rc.return_value = mock_redmine_client

            dm = DataManager()

            assert dm.config_manager == mock_config_manager
            assert dm.db_manager == mock_db_manager
            assert dm.redmine_client == mock_redmine_client

    def test_sync_project_success(self, data_manager):
        """Test successful project synchronization."""
        # Setup mock data
        project_data = RedmineProject(
            id=1,
            name="Test Project",
            identifier="test-project",
            description="A test project",
            status=1,
            created_on=datetime(2024, 1, 1),
            updated_on=datetime(2024, 1, 2),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            versions=[],
            custom_fields={},
        )
        tickets_data = [
            TicketData(
                id=1,
                subject="Test Ticket",
                estimated_hours=8.0,
                created_on=datetime(2024, 1, 1),
                updated_on=datetime(2024, 1, 2),
                status_id=1,
                status_name="New",
                assigned_to_id=None,
                assigned_to_name=None,
                project_id=1,
                version_id=None,
                version_name=None,
                custom_fields={},
            )
        ]

        data_manager.redmine_client.get_project_data.return_value = project_data
        data_manager.redmine_client.get_project_versions.return_value = []
        data_manager.redmine_client.get_project_tickets.return_value = tickets_data
        data_manager.redmine_client.get_all_project_journals.return_value = []

        result = data_manager.sync_project(1)

        assert result is None  # sync_project returns None on success
        data_manager.redmine_client.get_project_data.assert_called_once_with(1)
        data_manager.redmine_client.get_project_tickets.assert_called_once_with(
            1, include_closed=False
        )

    def test_sync_project_redmine_error(self, data_manager):
        """Test project synchronization with Redmine error."""
        data_manager.redmine_client.get_project_data.side_effect = Exception(
            "Redmine error"
        )

        with pytest.raises(DataManagerError, match="Project sync failed"):
            data_manager.sync_project(1)

    def test_fetch_project_updates_success(self, data_manager):
        """Test successful project updates fetching."""
        last_update = datetime(2024, 1, 5)
        data_manager.db_manager.get_last_update.return_value = last_update
        data_manager.redmine_client.get_updated_tickets.return_value = []

        result = data_manager.fetch_project_updates(1)

        assert result is None

    def test_fetch_project_updates_no_last_update(self, data_manager):
        """Test project updates fetching without last update."""
        data_manager.db_manager.get_last_update.return_value = None

        result = data_manager.fetch_project_updates(1)

        # Should perform full sync
        assert result is None

    def test_get_project_timeline_success(self, data_manager):
        """Test successful project timeline retrieval."""
        project_data = {"id": 1, "name": "Test Project"}
        snapshots_data = [
            {
                "date": "2024-01-01",
                "total_estimated_hours": 100.0,
                "remaining_hours": 100.0,
            }
        ]
        scope_changes_data = []

        data_manager.db_manager.get_project.return_value = project_data
        data_manager.db_manager.get_daily_snapshots.return_value = snapshots_data
        data_manager.db_manager.get_scope_changes.return_value = scope_changes_data

        result = data_manager.get_project_timeline(1)

        assert isinstance(result, dict)
        assert "project" in result
        assert "snapshots" in result
        assert "scope_changes" in result

    def test_get_project_timeline_not_found(self, data_manager):
        """Test project timeline retrieval when project not found."""
        # Override the mock to return None for fetchone
        mock_execute = Mock()
        mock_execute.fetchone.return_value = None
        mock_connection = Mock()
        mock_connection.execute.return_value = mock_execute
        data_manager.db_manager.get_connection.return_value.__enter__ = Mock(
            return_value=mock_connection
        )

        result = data_manager.get_project_timeline(1)

        assert result is None

    def test_get_project_timeline_database_error(self, data_manager):
        """Test project timeline retrieval with database error."""
        # Mock the connection to raise an error
        data_manager.db_manager.get_connection.side_effect = Exception("DB error")

        with pytest.raises(DataManagerError, match="Failed to get project timeline"):
            data_manager.get_project_timeline(1)

    def test_clear_project_cache_success(self, data_manager):
        """Test successful project cache clearing."""
        # The method doesn't use clear_project_data, it uses get_connection directly

        result = data_manager.clear_project_cache(1)

        assert result is None

    def test_clear_project_cache_database_error(self, data_manager):
        """Test project cache clearing with database error."""
        # Mock the connection to raise an error
        data_manager.db_manager.get_connection.side_effect = Exception("DB error")

        with pytest.raises(DataManagerError, match="Failed to clear cache"):
            data_manager.clear_project_cache(1)

    def test_get_cache_status_success(self, data_manager):
        """Test successful cache status retrieval."""
        result = data_manager.get_cache_status()

        assert isinstance(result, dict)
        assert "cache_directory" in result
        assert "database_info" in result

    def test_get_cache_status_database_error(self, data_manager):
        """Test cache status retrieval with database error."""
        data_manager.db_manager.get_database_info.side_effect = Exception("DB error")

        with pytest.raises(DataManagerError, match="Failed to get cache status"):
            data_manager.get_cache_status()

    def test_save_project_methods(self, data_manager):
        """Test project saving methods through sync_project."""
        project_data = RedmineProject(
            id=1,
            name="Test Project",
            identifier="test",
            description="Test",
            status=1,
            created_on=datetime(2024, 1, 1),
            updated_on=datetime(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            versions=[],
            custom_fields={},
        )
        tickets_data = []

        data_manager.redmine_client.get_project_data.return_value = project_data
        data_manager.redmine_client.get_project_versions.return_value = []
        data_manager.redmine_client.get_project_tickets.return_value = tickets_data
        data_manager.redmine_client.get_all_project_journals.return_value = []

        result = data_manager.sync_project(1)

        assert result is None  # sync_project returns None, not True
        # Verify that database connection is used (this tests _save_project was called)
        data_manager.db_manager.get_connection.assert_called()

    def test_build_daily_snapshots_through_sync(self, data_manager):
        """Test daily snapshots building through sync_project."""
        project_data = RedmineProject(
            id=1,
            name="Test Project",
            identifier="test",
            description="Test",
            status=1,
            created_on=datetime(2024, 1, 1),
            updated_on=datetime(2024, 1, 1),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            versions=[],
            custom_fields={},
        )
        tickets_data = [
            TicketData(
                id=1,
                subject="Test",
                estimated_hours=8.0,
                created_on=datetime(2024, 1, 1),
                updated_on=datetime(2024, 1, 1),
                status_id=1,
                status_name="New",
                assigned_to_id=None,
                assigned_to_name=None,
                project_id=1,
                version_id=None,
                version_name=None,
                custom_fields={},
            )
        ]

        data_manager.redmine_client.get_project_data.return_value = project_data
        data_manager.redmine_client.get_project_versions.return_value = []
        data_manager.redmine_client.get_project_tickets.return_value = tickets_data
        data_manager.redmine_client.get_all_project_journals.return_value = []

        result = data_manager.sync_project(1)

        assert result is None

    def test_private_methods_coverage(self, data_manager):
        """Test coverage of private methods through public methods."""
        # Test _get_project
        data_manager.db_manager.get_project.return_value = {"id": 1}
        result = data_manager._get_project(1)
        assert result["id"] == 1

        # Test _get_daily_snapshots
        data_manager.db_manager.get_daily_snapshots.return_value = []
        result = data_manager._get_daily_snapshots(1)
        assert result == []

        # Test _get_scope_changes
        data_manager.db_manager.get_scope_changes.return_value = []
        result = data_manager._get_scope_changes(1)
        assert result == []

    def test_is_ticket_completed_default_statuses(self, data_manager):
        """チケット完了判定 - デフォルト設定"""
        # デフォルト設定での完了ステータス
        assert data_manager._is_ticket_completed("完了") is True
        assert data_manager._is_ticket_completed("Closed") is True
        assert data_manager._is_ticket_completed("クローズ") is True

        # 非完了ステータス
        assert data_manager._is_ticket_completed("解決") is False
        assert data_manager._is_ticket_completed("Resolved") is False
        assert data_manager._is_ticket_completed("進行中") is False
        assert data_manager._is_ticket_completed("In Progress") is False
        assert data_manager._is_ticket_completed("新規") is False
        assert data_manager._is_ticket_completed("New") is False
        assert data_manager._is_ticket_completed(None) is False
        assert data_manager._is_ticket_completed("") is False

    def test_is_ticket_completed_custom_statuses(self, data_manager):
        """チケット完了判定 - カスタム設定"""
        # 設定を変更
        data_manager.config.data.completed_statuses = ["解決", "Done", "終了"]

        # カスタム完了ステータス
        assert data_manager._is_ticket_completed("解決") is True
        assert data_manager._is_ticket_completed("Done") is True
        assert data_manager._is_ticket_completed("終了") is True

        # 元のデフォルトステータスは非完了扱い
        assert data_manager._is_ticket_completed("完了") is False
        assert data_manager._is_ticket_completed("Closed") is False
        assert data_manager._is_ticket_completed("クローズ") is False

        # その他の非完了ステータス
        assert data_manager._is_ticket_completed("進行中") is False
        assert data_manager._is_ticket_completed("新規") is False
        assert data_manager._is_ticket_completed(None) is False


class TestGetDataManager:
    """Test get_data_manager factory function."""

    def test_get_data_manager_success(self):
        """Test successful data manager creation."""
        with patch(
            "rd_burndown.core.data_manager.DataManager"
        ) as mock_data_manager_class:
            mock_manager = Mock()
            mock_data_manager_class.return_value = mock_manager

            result = get_data_manager()

            assert result == mock_manager
            mock_data_manager_class.assert_called_once_with()

    def test_get_data_manager_error(self):
        """Test data manager creation error."""
        with patch(
            "rd_burndown.core.data_manager.DataManager"
        ) as mock_data_manager_class:
            mock_data_manager_class.side_effect = Exception("Manager error")

            with pytest.raises(DataManagerError, match="Failed to create data manager"):
                get_data_manager()
