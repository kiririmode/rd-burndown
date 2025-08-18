"""Redmine APIクライアントのテスト"""

import json
from datetime import datetime
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest
import requests

from rd_burndown.core.redmine_client import RedmineAPIError, RedmineClient
from rd_burndown.utils.config import Config


class TestRedmineAPIError:
    """RedmineAPIError のテスト"""

    def test_create_error_without_status_code(self):
        """ステータスコードなしでのエラー作成テスト"""
        error = RedmineAPIError("テストエラー")

        assert str(error) == "テストエラー"
        assert error.status_code is None

    def test_create_error_with_status_code(self):
        """ステータスコード付きでのエラー作成テスト"""
        error = RedmineAPIError("認証エラー", 401)

        assert str(error) == "認証エラー"
        assert error.status_code == 401


class TestRedmineClient:
    """RedmineClient のテスト"""

    def create_test_config(self) -> Config:
        """テスト用設定作成"""
        config = Config()
        config.redmine.url = "http://test.example.com"
        config.redmine.api_key = "test-api-key"  # pragma: allowlist secret
        config.redmine.timeout = 30
        config.redmine.verify_ssl = True
        return config

    def create_mock_response(
        self, status_code: int = 200, json_data: Optional[dict[str, Any]] = None
    ) -> Mock:
        """モックレスポンス作成"""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.ok = status_code < 400
        mock_response.json.return_value = json_data or {}
        mock_response.text = json.dumps(json_data or {})
        return mock_response

    def test_init(self):
        """初期化のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        assert client.base_url == "http://test.example.com"
        assert client.api_key == "test-api-key"  # pragma: allowlist secret
        assert client.timeout == 30
        assert client.verify_ssl is True

    def test_init_with_trailing_slash(self):
        """末尾スラッシュありURL初期化のテスト"""
        config = self.create_test_config()
        config.redmine.url = "http://test.example.com/"
        client = RedmineClient(config)

        # 末尾スラッシュが削除されているか確認
        assert client.base_url == "http://test.example.com"

    @patch("rd_burndown.core.redmine_client.requests.Session")
    def test_create_session(self, mock_session_class: Mock):
        """HTTPセッション作成のテスト"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        config = self.create_test_config()
        RedmineClient(config)

        # セッションが作成されているか確認
        mock_session_class.assert_called_once()

        # ヘッダーが設定されているか確認
        mock_session.headers.update.assert_called_once_with(
            {
                "Content-Type": "application/json",
                "X-Redmine-API-Key": "test-api-key",
            }
        )

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limit(self, mock_sleep: Mock, mock_time: Mock):
        """レート制限のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        # 最初のリクエスト時間を設定
        client._last_request_time = 0.0

        # 時間の経過をシミュレート
        mock_time.return_value = 0.1  # 0.1秒しか経過していない

        # レート制限実行
        client._rate_limit()

        # スリープが呼ばれたか確認（0.2 - 0.1 = 0.1秒）
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limit_no_sleep_needed(self, mock_sleep: Mock, mock_time: Mock):
        """レート制限（スリープ不要）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        # 最初のリクエスト時間を設定
        client._last_request_time = 0.0

        # 十分な時間が経過
        mock_time.return_value = 0.3  # 0.2秒以上経過

        client._rate_limit()

        # スリープが呼ばれないか確認
        mock_sleep.assert_not_called()

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_success(self, mock_request: Mock):
        """正常リクエストのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        # 正常レスポンスをモック
        mock_response = self.create_mock_response(200, {"test": "data"})
        mock_request.return_value = mock_response

        # リクエスト実行
        result = client._make_request("GET", "/test.json")

        # 結果確認
        assert result == {"test": "data"}

        # リクエストパラメータ確認
        mock_request.assert_called_once_with(
            method="GET",
            url="http://test.example.com/test.json",
            params=None,
            json=None,
            timeout=30,
            verify=True,
        )

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_with_params_and_data(self, mock_request: Mock):
        """パラメータ・データ付きリクエストのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = self.create_mock_response(200, {"result": "ok"})
        mock_request.return_value = mock_response

        params = {"limit": 50}
        data = {"name": "test"}

        result = client._make_request("POST", "/test.json", params=params, data=data)

        assert result == {"result": "ok"}
        mock_request.assert_called_once_with(
            method="POST",
            url="http://test.example.com/test.json",
            params=params,
            json=data,
            timeout=30,
            verify=True,
        )

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_401_error(self, mock_request: Mock):
        """401認証エラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = self.create_mock_response(401, {"error": "Unauthorized"})
        mock_request.return_value = mock_response

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "認証に失敗しました" in str(exc_info.value)
        assert exc_info.value.status_code == 401

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_403_error(self, mock_request: Mock):
        """403権限エラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = self.create_mock_response(403)
        mock_request.return_value = mock_response

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "アクセス権限がありません" in str(exc_info.value)
        assert exc_info.value.status_code == 403

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_404_error(self, mock_request: Mock):
        """404リソース未検出エラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = self.create_mock_response(404)
        mock_request.return_value = mock_response

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "リソースが見つかりません" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_500_error(self, mock_request: Mock):
        """500サーバーエラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = self.create_mock_response(500)
        mock_request.return_value = mock_response

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "API エラー: 500" in str(exc_info.value)
        assert exc_info.value.status_code == 500

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_connection_error(self, mock_request: Mock):
        """接続エラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "接続エラー" in str(exc_info.value)

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_timeout_error(self, mock_request: Mock):
        """タイムアウトエラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_request.side_effect = requests.exceptions.Timeout("Request timeout")

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "タイムアウトエラー" in str(exc_info.value)

    @patch("rd_burndown.core.redmine_client.requests.Session.request")
    def test_make_request_json_decode_error(self, mock_request: Mock):
        """JSON解析エラーのテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_request.return_value = mock_response

        with pytest.raises(RedmineAPIError) as exc_info:
            client._make_request("GET", "/test.json")

        assert "JSON パースエラー" in str(exc_info.value)

    @patch.object(RedmineClient, "_make_request")
    def test_get_projects(self, mock_make_request: Mock):
        """プロジェクト一覧取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_projects = [
            {"id": 1, "name": "Project 1"},
            {"id": 2, "name": "Project 2"},
        ]
        mock_make_request.return_value = {"projects": mock_projects}

        result = client.get_projects()

        assert result == mock_projects
        mock_make_request.assert_called_once_with(
            "GET",
            "/projects.json",
            params={
                "limit": 100,
                "include": "enabled_modules,versions",
                "status": "1",
            },
        )

    @patch.object(RedmineClient, "_make_request")
    def test_get_projects_include_closed(self, mock_make_request: Mock):
        """プロジェクト一覧取得（クローズ含む）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_make_request.return_value = {"projects": []}

        client.get_projects(include_closed=True)

        # statusパラメータが含まれないか確認
        call_args = mock_make_request.call_args
        assert "status" not in call_args[1]["params"]

    @patch.object(RedmineClient, "_make_request")
    def test_get_project(self, mock_make_request: Mock):
        """プロジェクト詳細取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_project = {"id": 1, "name": "Test Project"}
        mock_make_request.return_value = {"project": mock_project}

        result = client.get_project(1)

        assert result == mock_project
        mock_make_request.assert_called_once_with(
            "GET",
            "/projects/1.json",
            params={
                "include": "enabled_modules,versions,issue_categories,time_entry_activities"
            },
        )

    @patch.object(RedmineClient, "_make_request")
    def test_get_issues(self, mock_make_request: Mock):
        """チケット一覧取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_response = {
            "issues": [{"id": 1, "subject": "Test Issue"}],
            "total_count": 1,
        }
        mock_make_request.return_value = mock_response

        result = client.get_issues(1)

        assert result == mock_response
        mock_make_request.assert_called_once_with(
            "GET",
            "/issues.json",
            params={
                "project_id": 1,
                "limit": 100,
                "offset": 0,
                "include": "journals,relations",
                "status_id": "*",
            },
        )

    @patch.object(RedmineClient, "_make_request")
    def test_get_issues_with_updated_since(self, mock_make_request: Mock):
        """更新日指定チケット一覧取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_make_request.return_value = {"issues": []}

        updated_since = datetime(2024, 1, 15, 12, 0, 0)
        client.get_issues(1, updated_since=updated_since)

        call_args = mock_make_request.call_args
        params = call_args[1]["params"]
        assert params["updated_on"] == ">=2024-01-15T12:00:00Z"

    @patch.object(RedmineClient, "_make_request")
    def test_get_issues_exclude_closed(self, mock_make_request: Mock):
        """チケット一覧取得（クローズ除外）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_make_request.return_value = {"issues": []}

        client.get_issues(1, include_closed=False)

        call_args = mock_make_request.call_args
        params = call_args[1]["params"]
        assert params["status_id"] == "open"

    @patch.object(RedmineClient, "get_issues")
    def test_get_all_project_issues(self, mock_get_issues: Mock):
        """プロジェクト全チケット取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        # ページング有りのレスポンスをモック
        mock_get_issues.side_effect = [
            {
                "issues": [{"id": 1}, {"id": 2}],
                "total_count": 150,  # 複数ページ必要にする
            },
            {
                "issues": [{"id": 3}],
                "total_count": 150,
            },
        ]

        result = client.get_all_project_issues(1)

        # 2回呼び出される
        assert mock_get_issues.call_count == 2

        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert result[2]["id"] == 3

    @patch.object(RedmineClient, "_make_request")
    def test_get_issue(self, mock_make_request: Mock):
        """チケット詳細取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_issue = {"id": 1, "subject": "Test Issue"}
        mock_make_request.return_value = {"issue": mock_issue}

        result = client.get_issue(1)

        assert result == mock_issue
        mock_make_request.assert_called_once_with(
            "GET",
            "/issues/1.json",
            params={"include": "journals,relations,watchers,children,details"},
        )

    @patch.object(RedmineClient, "_make_request")
    def test_test_connection_success(self, mock_make_request: Mock):
        """接続テスト（成功）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_make_request.return_value = {"user": {"id": 1}}

        result = client.test_connection()

        assert result is True
        mock_make_request.assert_called_once_with("GET", "/users/current.json")

    @patch.object(RedmineClient, "_make_request")
    def test_test_connection_failure(self, mock_make_request: Mock):
        """接続テスト（失敗）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_make_request.side_effect = RedmineAPIError("Connection failed")

        result = client.test_connection()

        assert result is False

    @patch.object(RedmineClient, "_make_request")
    def test_get_current_user(self, mock_make_request: Mock):
        """現在ユーザー取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_user = {"id": 1, "login": "test_user"}
        mock_make_request.return_value = {"user": mock_user}

        result = client.get_current_user()

        assert result == mock_user
        mock_make_request.assert_called_once_with("GET", "/users/current.json")

    @patch.object(RedmineClient, "_make_request")
    def test_get_issue_statuses(self, mock_make_request: Mock):
        """チケットステータス一覧取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_statuses = [
            {"id": 1, "name": "新規"},
            {"id": 2, "name": "進行中"},
        ]
        mock_make_request.return_value = {"issue_statuses": mock_statuses}

        result = client.get_issue_statuses()

        assert result == mock_statuses
        mock_make_request.assert_called_once_with("GET", "/issue_statuses.json")

    @patch.object(RedmineClient, "_make_request")
    def test_get_trackers(self, mock_make_request: Mock):
        """トラッカー一覧取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_trackers = [
            {"id": 1, "name": "バグ"},
            {"id": 2, "name": "機能"},
        ]
        mock_make_request.return_value = {"trackers": mock_trackers}

        result = client.get_trackers()

        assert result == mock_trackers
        mock_make_request.assert_called_once_with("GET", "/trackers.json")

    @patch.object(RedmineClient, "_make_request")
    def test_get_users_all(self, mock_make_request: Mock):
        """ユーザー一覧取得（全体）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_users = [{"id": 1, "login": "user1"}]
        mock_make_request.return_value = {"users": mock_users}

        result = client.get_users()

        assert result == mock_users
        mock_make_request.assert_called_once_with(
            "GET", "/users.json", params={"limit": 100}
        )

    @patch.object(RedmineClient, "_make_request")
    def test_get_users_project_members(self, mock_make_request: Mock):
        """ユーザー一覧取得（プロジェクトメンバー）のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_memberships = [
            {"user": {"id": 1, "login": "user1"}},
            {"user": {"id": 2, "login": "user2"}},
        ]
        mock_make_request.return_value = {"memberships": mock_memberships}

        result = client.get_users(project_id=1)

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

        mock_make_request.assert_called_once_with(
            "GET", "/projects/1/memberships.json", params={"limit": 100}
        )

    @patch.object(RedmineClient, "_make_request")
    def test_get_versions(self, mock_make_request: Mock):
        """バージョン一覧取得のテスト"""
        config = self.create_test_config()
        client = RedmineClient(config)

        mock_versions = [
            {"id": 1, "name": "v1.0.0"},
            {"id": 2, "name": "v1.1.0"},
        ]
        mock_make_request.return_value = {"versions": mock_versions}

        result = client.get_versions(1)

        assert result == mock_versions
        mock_make_request.assert_called_once_with("GET", "/projects/1/versions.json")


class TestIntegration:
    """統合テスト"""

    @patch("rd_burndown.core.redmine_client.requests.Session")
    def test_client_initialization_and_configuration(self, mock_session_class: Mock):
        """クライアント初期化と設定の統合テスト"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        config = Config()
        config.redmine.url = "https://redmine.example.com/"
        config.redmine.api_key = "integration-test-key-789"  # pragma: allowlist secret
        config.redmine.timeout = 45
        config.redmine.verify_ssl = False

        client = RedmineClient(config)

        # 設定値が正しく適用されているか確認
        assert client.base_url == "https://redmine.example.com"
        assert client.api_key == "integration-test-key-789"  # pragma: allowlist secret
        assert client.timeout == 45
        assert client.verify_ssl is False

        # セッション設定の確認
        mock_session.headers.update.assert_called_once_with(
            {
                "Content-Type": "application/json",
                "X-Redmine-API-Key": "integration-test-key-789",
            }
        )

    @patch.object(RedmineClient, "_make_request")
    def test_full_api_workflow(self, mock_make_request: Mock):
        """完全なAPIワークフローのテスト"""
        config = Config()
        client = RedmineClient(config)

        # 複数のAPIエンドポイントを順次呼び出し
        mock_make_request.side_effect = [
            {"user": {"id": 1, "login": "admin"}},  # test_connection
            {"projects": [{"id": 1, "name": "Test Project"}]},  # get_projects
            {"project": {"id": 1, "name": "Test Project"}},  # get_project
            {"issues": [], "total_count": 0},  # get_issues
        ]

        # ワークフロー実行
        connection_ok = client.test_connection()
        assert connection_ok is True

        projects = client.get_projects()
        assert len(projects) == 1

        project = client.get_project(1)
        assert project["id"] == 1

        issues = client.get_issues(1)
        assert issues["total_count"] == 0

        # 正しい順序でAPIが呼ばれたか確認
        assert mock_make_request.call_count == 4
