"""データ管理・キャッシュシステム"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from rd_burndown.core.database import get_database_manager
from rd_burndown.core.models import (
    RedmineProject,
    TicketData,
)
from rd_burndown.core.redmine_client import get_redmine_client
from rd_burndown.utils.config import get_config_manager

logger = logging.getLogger(__name__)


class DataManagerError(Exception):
    """データ管理エラー"""


class DataManager:
    """データ管理・キャッシュシステム"""

    def __init__(self):
        """初期化"""
        self.config_manager = get_config_manager()
        self.config = self.config_manager.load_config()
        self.db_manager = get_database_manager()
        self.redmine_client = get_redmine_client()

        # キャッシュディレクトリの確保
        self.cache_dir = Path(self.config.data.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # データベースの初期化
        self.db_manager.initialize_database()

    def sync_project(
        self, project_id: int, force: bool = False, include_closed: bool = False
    ) -> None:
        """
        プロジェクト全体の同期・初期化

        Args:
            project_id: プロジェクトID
            force: 強制完全同期
            include_closed: 終了チケットも含める
        """
        logger.info(f"Starting project sync for project {project_id}")

        try:
            # プロジェクト情報の取得・更新
            project_data = self.redmine_client.get_project_data(project_id)
            self._save_project(project_data)

            # バージョン・マイルストーン情報の同期
            versions = self.redmine_client.get_project_versions(project_id)
            self._save_project_versions(project_id, versions)

            # チケット全体の同期
            tickets = self.redmine_client.get_project_tickets(
                project_id, include_closed=include_closed
            )

            # チケットデータの保存
            self._save_tickets(tickets)

            # 日次スナップショットの構築
            self._build_daily_snapshots(project_id)

            logger.info(f"Project sync completed for project {project_id}")

        except Exception as e:
            logger.error(f"Project sync failed for project {project_id}: {e}")
            raise DataManagerError(f"Project sync failed: {e}") from e

    def fetch_project_updates(
        self,
        project_id: int,
        incremental: bool = True,
        since_date: Optional[date] = None,
    ) -> None:
        """
        プロジェクトの増分更新

        Args:
            project_id: プロジェクトID
            incremental: 増分更新モード
            since_date: 指定日以降の変更のみ
        """
        logger.info(f"Fetching updates for project {project_id}")

        try:
            # 最後の更新日時を取得
            if incremental and since_date is None:
                since_date = self._get_last_update_date(project_id)

            # 更新されたチケットの取得
            updated_tickets = self.redmine_client.get_updated_tickets(
                project_id, since_date=since_date
            )

            if updated_tickets:
                # チケットデータの更新
                self._save_tickets(updated_tickets)

                # スコープ変更の検出・記録
                self._detect_scope_changes(project_id, updated_tickets)

                # 日次スナップショットの更新
                self._update_daily_snapshots(project_id, since_date)

                logger.info(
                    f"Updated {len(updated_tickets)} tickets for project {project_id}"
                )
            else:
                logger.info(f"No updates found for project {project_id}")

        except Exception as e:
            logger.error(f"Failed to fetch updates for project {project_id}: {e}")
            raise DataManagerError(f"Failed to fetch updates: {e}") from e

    def get_project_timeline(self, project_id: int) -> Optional[dict[str, Any]]:
        """
        プロジェクトの時系列データを取得

        Args:
            project_id: プロジェクトID

        Returns:
            プロジェクト時系列データ
        """
        try:
            # プロジェクト基本情報
            project = self._get_project(project_id)
            if not project:
                return None

            # 日次スナップショット
            snapshots = self._get_daily_snapshots(project_id)

            # スコープ変更履歴
            scope_changes = self._get_scope_changes(project_id)

            return {
                "project": project,
                "snapshots": snapshots,
                "scope_changes": scope_changes,
            }

        except Exception as e:
            logger.error(f"Failed to get project timeline for {project_id}: {e}")
            raise DataManagerError(f"Failed to get project timeline: {e}") from e

    def clear_project_cache(self, project_id: int) -> None:
        """
        プロジェクトのキャッシュをクリア

        Args:
            project_id: プロジェクトID
        """
        logger.info(f"Clearing cache for project {project_id}")

        try:
            with self.db_manager.get_connection() as conn:
                # 関連データの削除
                conn.execute(
                    "DELETE FROM scope_changes WHERE project_id = ?", (project_id,)
                )
                conn.execute(
                    "DELETE FROM daily_snapshots WHERE project_id = ?", (project_id,)
                )
                conn.execute("DELETE FROM tickets WHERE project_id = ?", (project_id,))
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                conn.commit()

            # JSONキャッシュファイルの削除
            cache_file = self.cache_dir / f"project_{project_id}.json"
            if cache_file.exists():
                cache_file.unlink()

            logger.info(f"Cache cleared for project {project_id}")

        except Exception as e:
            logger.error(f"Failed to clear cache for project {project_id}: {e}")
            raise DataManagerError(f"Failed to clear cache: {e}") from e

    def get_cache_status(self, project_id: Optional[int] = None) -> dict[str, Any]:
        """
        キャッシュ状態の取得

        Args:
            project_id: プロジェクトID（Noneの場合は全体）

        Returns:
            キャッシュ状態情報
        """
        try:
            db_info = self.db_manager.get_database_info()

            if project_id:
                # 特定プロジェクトの情報
                with self.db_manager.get_connection(read_only=True) as conn:
                    # プロジェクト情報
                    project_row = conn.execute(
                        "SELECT * FROM projects WHERE id = ?", (project_id,)
                    ).fetchone()

                    if not project_row:
                        return {"error": f"Project {project_id} not found"}

                    # 各テーブルの件数
                    tickets_count = conn.execute(
                        "SELECT COUNT(*) FROM tickets WHERE project_id = ?",
                        (project_id,),
                    ).fetchone()[0]

                    snapshots_count = conn.execute(
                        "SELECT COUNT(*) FROM daily_snapshots WHERE project_id = ?",
                        (project_id,),
                    ).fetchone()[0]

                    scope_changes_count = conn.execute(
                        "SELECT COUNT(*) FROM scope_changes WHERE project_id = ?",
                        (project_id,),
                    ).fetchone()[0]

                    # 最終更新日時
                    last_update = conn.execute(
                        "SELECT MAX(updated_at) FROM tickets WHERE project_id = ?",
                        (project_id,),
                    ).fetchone()[0]

                    return {
                        "project_id": project_id,
                        "project_name": project_row["name"],
                        "tickets_count": tickets_count,
                        "snapshots_count": snapshots_count,
                        "scope_changes_count": scope_changes_count,
                        "last_update": last_update,
                        "database_size": db_info["file_size_bytes"],
                    }
            else:
                # 全体の情報
                return {
                    "database_info": db_info,
                    "cache_directory": str(self.cache_dir),
                    "cache_ttl_hours": self.config.data.cache_ttl_hours,
                }

        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            raise DataManagerError(f"Failed to get cache status: {e}") from e

    def _save_project(self, project_data: RedmineProject) -> None:
        """プロジェクト情報の保存"""
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects
                (id, name, identifier, description, status, start_date, end_date,
                 created_on, updated_on, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_data.id,
                    project_data.name,
                    project_data.identifier,
                    project_data.description,
                    project_data.status,
                    project_data.start_date,
                    project_data.end_date,
                    project_data.created_on,
                    project_data.updated_on,
                    datetime.now(),
                ),
            )
            conn.commit()

    def _save_project_versions(
        self, project_id: int, versions: list[dict[str, Any]]
    ) -> None:
        """プロジェクトバージョン情報の保存（JSONキャッシュ）"""
        cache_file = self.cache_dir / f"project_{project_id}_versions.json"
        cache_data = {
            "project_id": project_id,
            "versions": versions,
            "updated_at": datetime.now().isoformat(),
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def _save_tickets(self, tickets: list[TicketData]) -> None:
        """チケットデータの保存"""
        if not tickets:
            return

        ticket_data = []
        for ticket in tickets:
            ticket_data.append(
                (
                    ticket.id,
                    ticket.project_id,
                    ticket.subject,
                    ticket.estimated_hours,
                    ticket.status_id,
                    ticket.status_name,
                    ticket.created_on,
                    ticket.updated_on,
                    ticket.completion_date(),
                    ticket.assigned_to_id,
                    ticket.assigned_to_name,
                    ticket.version_id,
                    ticket.version_name,
                    json.dumps(ticket.custom_fields) if ticket.custom_fields else None,
                    datetime.now(),
                )
            )

        query = """
            INSERT OR REPLACE INTO tickets
            (id, project_id, subject, estimated_hours, status_id, status_name,
             created_on, updated_on, completed_on, assigned_to_id, assigned_to_name,
             version_id, version_name, custom_fields, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db_manager.execute_many(query, ticket_data)

    def _build_daily_snapshots(self, project_id: int) -> None:
        """日次スナップショットの構築"""
        logger.info(f"Building daily snapshots for project {project_id}")

        # プロジェクトの期間を取得
        project = self._get_project(project_id)
        if not project:
            return

        # 開始日から現在日までの全日付を取得
        start_date = project.get("start_date")
        if not start_date:
            # プロジェクト開始日が設定されていない場合、最初のチケット作成日を使用
            with self.db_manager.get_connection(read_only=True) as conn:
                result = conn.execute(
                    "SELECT MIN(DATE(created_on)) FROM tickets WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                if result[0]:
                    # データベースから取得した文字列を日付に変換
                    start_date = datetime.fromisoformat(result[0]).date()
                else:
                    start_date = date.today()
        elif isinstance(start_date, str):
            # 文字列の場合は日付に変換
            start_date = datetime.fromisoformat(start_date).date()
        elif isinstance(start_date, date):
            # 既に日付型の場合はそのまま使用
            pass
        else:
            # その他の場合は現在日を使用
            start_date = date.today()

        end_date = date.today()

        # 各日付のスナップショットを作成
        current_date = start_date
        while current_date <= end_date:
            self._create_daily_snapshot(project_id, current_date)
            current_date += timedelta(days=1)

    def _create_daily_snapshot(self, project_id: int, target_date: date) -> None:
        """指定日の日次スナップショットを作成"""
        with self.db_manager.get_connection() as conn:
            # その日時点でのチケット状態を計算
            total_hours = 0.0
            completed_hours = 0.0
            active_count = 0
            completed_count = 0

            # チケット情報を取得（その日時点での状態）
            cursor = conn.execute(
                """
                SELECT estimated_hours, status_id, completed_on
                FROM tickets
                WHERE project_id = ?
                AND DATE(created_on) <= ?
                """,
                (project_id, target_date),
            )

            for row in cursor.fetchall():
                estimated_hours = row["estimated_hours"] or 0.0
                completed_on = row["completed_on"]

                total_hours += estimated_hours

                # 完了判定（その日時点で完了していたか）
                if completed_on:
                    try:
                        completed_date = datetime.fromisoformat(completed_on).date()
                        if completed_date <= target_date:
                            completed_hours += estimated_hours
                            completed_count += 1
                        else:
                            active_count += 1
                    except (ValueError, TypeError):
                        # 日付変換に失敗した場合は未完了として扱う
                        active_count += 1
                else:
                    active_count += 1

            remaining_hours = total_hours - completed_hours

            # スナップショットを保存
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_snapshots
                (date, project_id, total_estimated_hours, completed_hours, remaining_hours,
                 active_ticket_count, completed_ticket_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_date,
                    project_id,
                    total_hours,
                    completed_hours,
                    remaining_hours,
                    active_count,
                    completed_count,
                    datetime.now(),
                ),
            )
            conn.commit()

    def _detect_scope_changes(
        self, project_id: int, updated_tickets: list[TicketData]
    ) -> None:
        """スコープ変更の検出・記録"""
        for ticket in updated_tickets:
            # 既存チケットデータと比較
            with self.db_manager.get_connection(read_only=True) as conn:
                existing = conn.execute(
                    "SELECT estimated_hours FROM tickets WHERE id = ?", (ticket.id,)
                ).fetchone()

                if existing:
                    old_hours = existing["estimated_hours"] or 0.0
                    new_hours = ticket.estimated_hours or 0.0

                    if old_hours != new_hours:
                        # スコープ変更を記録
                        self._record_scope_change(
                            project_id,
                            ticket,
                            "modified",
                            new_hours - old_hours,
                            old_hours,
                            new_hours,
                        )
                else:
                    # 新規チケット
                    if ticket.estimated_hours:
                        self._record_scope_change(
                            project_id,
                            ticket,
                            "added",
                            ticket.estimated_hours,
                            None,
                            ticket.estimated_hours,
                        )

    def _record_scope_change(
        self,
        project_id: int,
        ticket: TicketData,
        change_type: str,
        hours_delta: float,
        old_hours: Optional[float],
        new_hours: Optional[float],
    ) -> None:
        """スコープ変更の記録"""
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scope_changes
                (date, project_id, ticket_id, ticket_subject, change_type,
                 hours_delta, old_hours, new_hours, reason, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date.today(),
                    project_id,
                    ticket.id,
                    ticket.subject,
                    change_type,
                    hours_delta,
                    old_hours,
                    new_hours,
                    f"Ticket {change_type}",
                    datetime.now(),
                ),
            )
            conn.commit()

    def _update_daily_snapshots(
        self, project_id: int, since_date: Optional[date]
    ) -> None:
        """日次スナップショットの更新"""
        if since_date is None:
            since_date = date.today() - timedelta(days=7)  # デフォルトで過去7日間

        # 更新対象日付から現在日まで再計算
        current_date = since_date
        while current_date <= date.today():
            self._create_daily_snapshot(project_id, current_date)
            current_date += timedelta(days=1)

    def _get_last_update_date(self, project_id: int) -> Optional[date]:
        """最後の更新日時を取得"""
        with self.db_manager.get_connection(read_only=True) as conn:
            result = conn.execute(
                "SELECT MAX(DATE(updated_at)) FROM tickets WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if result and result[0]:
                return datetime.fromisoformat(result[0]).date()
            return None

    def _get_project(self, project_id: int) -> Optional[dict[str, Any]]:
        """プロジェクト情報の取得"""
        with self.db_manager.get_connection(read_only=True) as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return dict(row) if row else None

    def _get_daily_snapshots(self, project_id: int) -> list[dict[str, Any]]:
        """日次スナップショットの取得"""
        with self.db_manager.get_connection(read_only=True) as conn:
            rows = conn.execute(
                "SELECT * FROM daily_snapshots WHERE project_id = ? ORDER BY date",
                (project_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def _get_scope_changes(self, project_id: int) -> list[dict[str, Any]]:
        """スコープ変更履歴の取得"""
        with self.db_manager.get_connection(read_only=True) as conn:
            rows = conn.execute(
                "SELECT * FROM scope_changes WHERE project_id = ? ORDER BY date",
                (project_id,),
            ).fetchall()
            return [dict(row) for row in rows]


def get_data_manager() -> DataManager:
    """
    データマネージャーの取得

    Returns:
        DataManager: データマネージャーインスタンス

    Raises:
        DataManagerError: データマネージャー作成に失敗した場合
    """
    try:
        return DataManager()
    except Exception as e:
        raise DataManagerError(f"Failed to create data manager: {e}") from e
