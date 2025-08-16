"""Redmine API クライアント"""

import json
import time
from datetime import datetime
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..utils.config import Config


class RedmineAPIError(Exception):
    """Redmine API エラー"""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RedmineClient:
    """Redmine REST API クライアント"""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = config.redmine.url.rstrip("/")
        self.api_key = config.redmine.api_key
        self.timeout = config.redmine.timeout
        self.verify_ssl = config.redmine.verify_ssl

        self.session = self._create_session()
        self._last_request_time = 0.0
        self._min_request_interval = 0.2  # 5 requests per second max

    def _create_session(self) -> requests.Session:
        """HTTPセッションを作成"""
        session = requests.Session()

        # リトライ戦略設定
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # ヘッダー設定
        session.headers.update(
            {
                "Content-Type": "application/json",
                "X-Redmine-API-Key": self.api_key,
            }
        )

        return session

    def _rate_limit(self) -> None:
        """レート制限実装"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time

        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)

        self._last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """API リクエスト実行"""
        self._rate_limit()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

            if response.status_code == 401:
                raise RedmineAPIError(
                    "認証に失敗しました。APIキーを確認してください。",
                    response.status_code,
                )
            if response.status_code == 403:
                raise RedmineAPIError(
                    "アクセス権限がありません。", response.status_code
                )
            if response.status_code == 404:
                raise RedmineAPIError(
                    "リソースが見つかりません。", response.status_code
                )
            if not response.ok:
                raise RedmineAPIError(
                    f"API エラー: {response.status_code} - {response.text}",
                    response.status_code,
                )

            return response.json()

        except requests.exceptions.ConnectionError as e:
            raise RedmineAPIError(f"接続エラー: {e}") from e
        except requests.exceptions.Timeout as e:
            raise RedmineAPIError(f"タイムアウトエラー: {e}") from e
        except requests.exceptions.RequestException as e:
            raise RedmineAPIError(f"リクエストエラー: {e}") from e
        except json.JSONDecodeError as e:
            raise RedmineAPIError(f"JSON パースエラー: {e}") from e

    def get_projects(self, include_closed: bool = False) -> list[dict[str, Any]]:
        """プロジェクト一覧取得"""
        params = {
            "limit": 100,
            "include": "enabled_modules,versions",
        }

        if not include_closed:
            params["status"] = "1"  # アクティブのみ

        response = self._make_request("GET", "/projects.json", params=params)
        return response.get("projects", [])

    def get_project(self, project_id: int) -> dict[str, Any]:
        """プロジェクト詳細取得"""
        params = {
            "include": "enabled_modules,versions,issue_categories,time_entry_activities",
        }

        response = self._make_request(
            "GET", f"/projects/{project_id}.json", params=params
        )
        return response.get("project", {})

    def get_issues(
        self,
        project_id: int,
        limit: int = 100,
        offset: int = 0,
        updated_since: Optional[datetime] = None,
        include_closed: bool = True,
    ) -> dict[str, Any]:
        """チケット一覧取得"""
        params = {
            "project_id": project_id,
            "limit": min(limit, 100),  # API制限
            "offset": offset,
            "include": "journals,relations",
        }

        if updated_since:
            params["updated_on"] = f">={updated_since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        if not include_closed:
            params["status_id"] = "open"

        return self._make_request("GET", "/issues.json", params=params)

    def get_issue(self, issue_id: int) -> dict[str, Any]:
        """チケット詳細取得"""
        params = {
            "include": "journals,relations,watchers,children",
        }

        response = self._make_request("GET", f"/issues/{issue_id}.json", params=params)
        return response.get("issue", {})

    def get_all_project_issues(
        self,
        project_id: int,
        updated_since: Optional[datetime] = None,
        include_closed: bool = True,
    ) -> list[dict[str, Any]]:
        """プロジェクトの全チケット取得（ページング対応）"""
        all_issues: list[dict[str, Any]] = []
        offset = 0
        limit = 100

        while True:
            response = self.get_issues(
                project_id=project_id,
                limit=limit,
                offset=offset,
                updated_since=updated_since,
                include_closed=include_closed,
            )

            issues = response.get("issues", [])
            if not issues:
                break

            all_issues.extend(issues)

            # ページング判定
            total_count = response.get("total_count", 0)
            if offset + limit >= total_count:
                break

            offset += limit

        return all_issues

    def get_issue_statuses(self) -> list[dict[str, Any]]:
        """チケットステータス一覧取得"""
        response = self._make_request("GET", "/issue_statuses.json")
        return response.get("issue_statuses", [])

    def get_trackers(self) -> list[dict[str, Any]]:
        """トラッカー一覧取得"""
        response = self._make_request("GET", "/trackers.json")
        return response.get("trackers", [])

    def get_users(self, project_id: Optional[int] = None) -> list[dict[str, Any]]:
        """ユーザー一覧取得"""
        params = {"limit": 100}

        if project_id is not None:
            # プロジェクトメンバーのみ取得
            response = self._make_request(
                "GET", f"/projects/{project_id}/memberships.json", params=params
            )
            memberships = response.get("memberships", [])
            users: list[dict[str, Any]] = []
            for membership in memberships:
                user = membership.get("user")
                if user:
                    users.append(user)
            return users
        response = self._make_request("GET", "/users.json", params=params)
        return response.get("users", [])

    def get_versions(self, project_id: int) -> list[dict[str, Any]]:
        """バージョン一覧取得"""
        response = self._make_request("GET", f"/projects/{project_id}/versions.json")
        return response.get("versions", [])

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            self._make_request("GET", "/users/current.json")
            return True
        except RedmineAPIError:
            return False

    def get_current_user(self) -> dict[str, Any]:
        """現在のユーザー情報取得"""
        response = self._make_request("GET", "/users/current.json")
        return response.get("user", {})
