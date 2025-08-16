"""pytest設定とフィクスチャ"""

import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from rd_burndown.core.models import (
    DailySnapshot,
    ProjectTimeline,
    RedmineProject,
    ScopeChange,
    TicketData,
)
from rd_burndown.utils.config import Config, ConfigManager


@pytest.fixture
def temp_dir():
    """一時ディレクトリフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config() -> Config:
    """サンプル設定フィクスチャ"""
    config = Config()
    config.redmine.url = "http://test.example.com"
    config.redmine.api_key = "test-api-key-12345"  # pragma: allowlist secret
    config.redmine.timeout = 30
    config.output.output_dir = "./test-output"
    config.data.cache_dir = "./test-cache"
    return config


@pytest.fixture
def config_manager(temp_dir: Path) -> ConfigManager:
    """設定マネージャーフィクスチャ"""
    config_path = temp_dir / "test-config.yaml"
    return ConfigManager(config_path)


@pytest.fixture
def sample_ticket() -> TicketData:
    """サンプルチケットフィクスチャ"""
    return TicketData(
        id=1,
        subject="テストチケット",
        estimated_hours=8.0,
        created_on=datetime(2024, 1, 1, 9, 0, 0),
        updated_on=datetime(2024, 1, 5, 17, 0, 0),
        status_id=1,
        status_name="新規",
        assigned_to_id=100,
        assigned_to_name="山田太郎",
        project_id=1,
        version_id=1,
        version_name="v1.0.0",
        custom_fields={"priority": "高"},
    )


@pytest.fixture
def sample_tickets() -> list[TicketData]:
    """サンプルチケット群フィクスチャ"""
    return [
        TicketData(
            id=1,
            subject="ユーザー認証機能",
            estimated_hours=16.0,
            created_on=datetime(2024, 1, 1, 9, 0, 0),
            updated_on=datetime(2024, 1, 5, 17, 0, 0),
            status_id=1,
            status_name="新規",
            assigned_to_id=100,
            assigned_to_name="山田太郎",
            project_id=1,
            version_id=1,
            version_name="v1.0.0",
            custom_fields={},
        ),
        TicketData(
            id=2,
            subject="データベース設計",
            estimated_hours=8.0,
            created_on=datetime(2024, 1, 2, 10, 0, 0),
            updated_on=datetime(2024, 1, 10, 16, 0, 0),
            status_id=3,  # 完了
            status_name="完了",
            assigned_to_id=101,
            assigned_to_name="佐藤花子",
            project_id=1,
            version_id=1,
            version_name="v1.0.0",
            custom_fields={},
        ),
        TicketData(
            id=3,
            subject="API実装",
            estimated_hours=24.0,
            created_on=datetime(2024, 1, 3, 11, 0, 0),
            updated_on=datetime(2024, 1, 15, 18, 0, 0),
            status_id=2,
            status_name="進行中",
            assigned_to_id=102,
            assigned_to_name="田中一郎",
            project_id=1,
            version_id=2,
            version_name="v1.1.0",
            custom_fields={},
        ),
    ]


@pytest.fixture
def sample_snapshot() -> DailySnapshot:
    """サンプルスナップショットフィクスチャ"""
    return DailySnapshot(
        date=date(2024, 1, 15),
        project_id=1,
        total_estimated_hours=100.0,
        completed_hours=30.0,
        remaining_hours=70.0,
        new_tickets_hours=5.0,
        changed_hours=2.0,
        deleted_hours=1.0,
        active_ticket_count=8,
        completed_ticket_count=2,
    )


@pytest.fixture
def sample_snapshots() -> list[DailySnapshot]:
    """サンプルスナップショット群フィクスチャ"""
    return [
        DailySnapshot(
            date=date(2024, 1, 1),
            project_id=1,
            total_estimated_hours=100.0,
            completed_hours=0.0,
            remaining_hours=100.0,
            new_tickets_hours=0.0,
            changed_hours=0.0,
            deleted_hours=0.0,
            active_ticket_count=10,
            completed_ticket_count=0,
        ),
        DailySnapshot(
            date=date(2024, 1, 15),
            project_id=1,
            total_estimated_hours=105.0,
            completed_hours=30.0,
            remaining_hours=75.0,
            new_tickets_hours=5.0,
            changed_hours=0.0,
            deleted_hours=0.0,
            active_ticket_count=8,
            completed_ticket_count=2,
        ),
        DailySnapshot(
            date=date(2024, 1, 31),
            project_id=1,
            total_estimated_hours=105.0,
            completed_hours=105.0,
            remaining_hours=0.0,
            new_tickets_hours=0.0,
            changed_hours=0.0,
            deleted_hours=0.0,
            active_ticket_count=0,
            completed_ticket_count=10,
        ),
    ]


@pytest.fixture
def sample_scope_change() -> ScopeChange:
    """サンプルスコープ変更フィクスチャ"""
    return ScopeChange(
        date=date(2024, 1, 10),
        project_id=1,
        change_type="added",
        ticket_id=123,
        ticket_subject="新機能追加",
        hours_delta=16.0,
        old_hours=None,
        new_hours=16.0,
        reason="要件追加",
    )


@pytest.fixture
def sample_scope_changes() -> list[ScopeChange]:
    """サンプルスコープ変更群フィクスチャ"""
    return [
        ScopeChange(
            date=date(2024, 1, 10),
            project_id=1,
            change_type="added",
            ticket_id=123,
            ticket_subject="新機能追加",
            hours_delta=8.0,
            old_hours=None,
            new_hours=8.0,
            reason="要件追加",
        ),
        ScopeChange(
            date=date(2024, 1, 20),
            project_id=1,
            change_type="modified",
            ticket_id=124,
            ticket_subject="機能変更",
            hours_delta=4.0,
            old_hours=16.0,
            new_hours=20.0,
            reason="仕様変更",
        ),
        ScopeChange(
            date=date(2024, 1, 25),
            project_id=1,
            change_type="removed",
            ticket_id=125,
            ticket_subject="機能削除",
            hours_delta=-8.0,
            old_hours=8.0,
            new_hours=None,
            reason="要件削除",
        ),
    ]


@pytest.fixture
def sample_project() -> RedmineProject:
    """サンプルプロジェクトフィクスチャ"""
    return RedmineProject(
        id=1,
        name="テストプロジェクト",
        identifier="test-project",
        description="テスト用プロジェクト",
        status=1,
        created_on=datetime(2024, 1, 1, 9, 0, 0),
        updated_on=datetime(2024, 1, 15, 17, 0, 0),
        versions=[
            {"id": 1, "name": "v1.0.0", "status": "open"},
            {"id": 2, "name": "v1.1.0", "status": "open"},
            {"id": 3, "name": "v0.9.0", "status": "closed"},
        ],
        custom_fields={"category": "開発"},
    )


@pytest.fixture
def sample_timeline(
    sample_snapshots: list[DailySnapshot], sample_scope_changes: list[ScopeChange]
) -> ProjectTimeline:
    """サンプルタイムラインフィクスチャ"""
    return ProjectTimeline(
        project_id=1,
        project_name="テストプロジェクト",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        snapshots=sample_snapshots,
        scope_changes=sample_scope_changes,
    )


@pytest.fixture
def mock_redmine_api_response() -> dict[str, Any]:
    """モックRedmine APIレスポンスフィクスチャ"""
    return {
        "projects": [
            {
                "id": 1,
                "name": "テストプロジェクト",
                "identifier": "test-project",
                "description": "テスト用プロジェクト",
                "status": 1,
                "created_on": "2024-01-01T09:00:00Z",
                "updated_on": "2024-01-15T17:00:00Z",
            }
        ],
        "issues": [
            {
                "id": 1,
                "subject": "テストチケット",
                "estimated_hours": 8.0,
                "created_on": "2024-01-01T09:00:00Z",
                "updated_on": "2024-01-05T17:00:00Z",
                "status": {"id": 1, "name": "新規"},
                "project": {"id": 1, "name": "テストプロジェクト"},
                "assigned_to": {"id": 100, "name": "山田太郎"},
                "fixed_version": {"id": 1, "name": "v1.0.0"},
            }
        ],
        "users": [
            {
                "id": 1,
                "login": "admin",
                "firstname": "管理者",
                "lastname": "ユーザー",
                "mail": "admin@example.com",
                "admin": True,
            }
        ],
        "issue_statuses": [
            {"id": 1, "name": "新規"},
            {"id": 2, "name": "進行中"},
            {"id": 3, "name": "完了"},
        ],
        "trackers": [
            {"id": 1, "name": "バグ"},
            {"id": 2, "name": "機能"},
            {"id": 3, "name": "サポート"},
        ],
    }


@pytest.fixture
def mock_redmine_client():
    """モックRedmineクライアントフィクスチャ"""
    client = Mock()
    client.test_connection.return_value = True
    client.get_current_user.return_value = {
        "id": 1,
        "login": "admin",
        "mail": "admin@example.com",
    }
    client.get_projects.return_value = [
        {"id": 1, "name": "テストプロジェクト", "identifier": "test-project"}
    ]
    client.get_project.return_value = {
        "id": 1,
        "name": "テストプロジェクト",
        "identifier": "test-project",
    }
    client.get_issues.return_value = {
        "issues": [],
        "total_count": 0,
    }
    return client


@pytest.fixture(autouse=True)
def reset_config_cache():
    """設定キャッシュリセット（各テスト前に自動実行）"""
    # ConfigManagerのキャッシュをクリア
    yield
    # テスト後のクリーンアップは不要


# テスト用のマーカー定義は pyproject.toml で行う
