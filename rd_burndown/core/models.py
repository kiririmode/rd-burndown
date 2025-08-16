"""データモデル定義"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

import pendulum


@dataclass
class TicketData:
    """チケットデータモデル"""

    id: int
    subject: str
    estimated_hours: Optional[float]
    created_on: datetime
    updated_on: datetime
    status_id: int
    status_name: str
    assigned_to_id: Optional[int]
    assigned_to_name: Optional[str]
    project_id: int
    version_id: Optional[int]
    version_name: Optional[str]
    custom_fields: dict[str, Any]

    def is_completed(self) -> bool:
        """完了状態判定

        Redmineのデフォルト完了ステータスIDは3, 5, 6
        """
        completed_status_ids = {3, 5, 6}
        return self.status_id in completed_status_ids

    def completion_date(self) -> Optional[datetime]:
        """完了日取得

        完了状態の場合は更新日を完了日とする
        """
        return self.updated_on if self.is_completed() else None

    def estimated_hours_safe(self) -> float:
        """予定工数の安全な取得（Noneの場合は0.0）"""
        return self.estimated_hours or 0.0


@dataclass
class DailySnapshot:
    """日次工数スナップショット"""

    date: date
    project_id: int
    total_estimated_hours: float
    completed_hours: float
    remaining_hours: float
    new_tickets_hours: float
    changed_hours: float
    deleted_hours: float
    active_ticket_count: int
    completed_ticket_count: int

    def burn_rate(self) -> float:
        """バーンレート計算（1日あたりの完了工数）"""
        return self.completed_hours

    def scope_change(self) -> float:
        """スコープ変更量計算（新規追加 + 変更 - 削除）"""
        return self.new_tickets_hours + self.changed_hours - self.deleted_hours

    def total_tickets(self) -> int:
        """総チケット数"""
        return self.active_ticket_count + self.completed_ticket_count

    def completion_rate(self) -> float:
        """完了率（%）"""
        total = self.total_tickets()
        return (self.completed_ticket_count / total * 100) if total > 0 else 0.0


@dataclass
class ScopeChange:
    """スコープ変更履歴"""

    date: date
    project_id: int
    change_type: str  # 'added', 'modified', 'removed'
    ticket_id: int
    ticket_subject: str
    hours_delta: float
    old_hours: Optional[float]
    new_hours: Optional[float]
    reason: str

    def impact_level(self) -> str:
        """影響度判定（high/medium/low）"""
        abs_delta = abs(self.hours_delta)
        if abs_delta >= 40.0:
            return "high"
        if abs_delta >= 8.0:
            return "medium"
        return "low"

    def is_scope_increase(self) -> bool:
        """スコープ増加判定"""
        return self.hours_delta > 0

    def is_scope_decrease(self) -> bool:
        """スコープ減少判定"""
        return self.hours_delta < 0


@dataclass
class ProjectTimeline:
    """プロジェクト時系列データ"""

    project_id: int
    project_name: str
    start_date: date
    end_date: Optional[date]
    snapshots: list[DailySnapshot]
    scope_changes: list[ScopeChange]

    def ideal_line(self) -> list[tuple[date, float]]:
        """理想線計算"""
        if not self.snapshots or self.end_date is None:
            return []

        first_snapshot = self.snapshots[0]
        initial_hours = first_snapshot.total_estimated_hours

        start = pendulum.instance(
            datetime.combine(self.start_date, datetime.min.time())
        )
        end = pendulum.instance(datetime.combine(self.end_date, datetime.min.time()))

        total_days = (end - start).days
        if total_days <= 0:
            return [(self.start_date, initial_hours), (self.end_date, 0.0)]

        daily_burn = initial_hours / total_days

        ideal_points: list[tuple[date, float]] = []
        current_date = self.start_date
        remaining_hours = initial_hours

        while current_date <= self.end_date:
            ideal_points.append((current_date, max(0.0, remaining_hours)))
            remaining_hours -= daily_burn
            current_date = (
                pendulum.instance(datetime.combine(current_date, datetime.min.time()))
                .add(days=1)
                .date()
            )

        return ideal_points

    def actual_line(self) -> list[tuple[date, float]]:
        """実際線計算"""
        return [
            (snapshot.date, snapshot.remaining_hours) for snapshot in self.snapshots
        ]

    def dynamic_ideal_line(self) -> list[tuple[date, float]]:
        """動的理想線計算（スコープ変更考慮）"""
        if not self.snapshots or self.end_date is None:
            return []

        dynamic_points: list[tuple[date, float]] = []

        for snapshot in self.snapshots:
            remaining_days = (self.end_date - snapshot.date).days
            if remaining_days <= 0:
                dynamic_points.append((snapshot.date, 0.0))
            else:
                dynamic_points.append((snapshot.date, snapshot.remaining_hours))

        return dynamic_points

    def scope_trend_line(self) -> list[tuple[date, float]]:
        """総工数推移線計算"""
        return [
            (snapshot.date, snapshot.total_estimated_hours)
            for snapshot in self.snapshots
        ]

    def get_snapshot_by_date(self, target_date: date) -> Optional[DailySnapshot]:
        """指定日のスナップショット取得"""
        for snapshot in self.snapshots:
            if snapshot.date == target_date:
                return snapshot
        return None

    def get_scope_changes_by_date(self, target_date: date) -> list[ScopeChange]:
        """指定日のスコープ変更取得"""
        return [change for change in self.scope_changes if change.date == target_date]

    def total_scope_change(self) -> float:
        """総スコープ変更量"""
        return sum(change.hours_delta for change in self.scope_changes)

    def current_status(self) -> Optional[DailySnapshot]:
        """現在のステータス（最新スナップショット）"""
        return self.snapshots[-1] if self.snapshots else None


@dataclass
class RedmineProject:
    """Redmineプロジェクトデータ"""

    id: int
    name: str
    identifier: str
    description: str
    status: int
    created_on: datetime
    updated_on: datetime
    versions: list[dict[str, Any]]
    custom_fields: dict[str, Any]

    def active_versions(self) -> list[dict[str, Any]]:
        """アクティブバージョン取得"""
        return [version for version in self.versions if version.get("status") == "open"]

    def is_active(self) -> bool:
        """プロジェクトがアクティブか判定"""
        return self.status == 1

    def is_closed(self) -> bool:
        """プロジェクトがクローズされているか判定"""
        return self.status == 5

    def get_version_by_id(self, version_id: int) -> Optional[dict[str, Any]]:
        """ID指定でバージョン取得"""
        for version in self.versions:
            if version.get("id") == version_id:
                return version
        return None


@dataclass
class ProjectSummary:
    """プロジェクトサマリー"""

    project: RedmineProject
    timeline: ProjectTimeline
    total_tickets: int
    completed_tickets: int
    total_estimated_hours: float
    completed_hours: float
    remaining_hours: float
    days_elapsed: int
    days_remaining: Optional[int]
    completion_rate: float
    average_burn_rate: float
    estimated_completion_date: Optional[date]

    def is_on_track(self) -> bool:
        """予定通り進行しているか判定"""
        if self.days_remaining is None or self.days_remaining <= 0:
            return self.remaining_hours <= 0

        required_burn_rate = self.remaining_hours / self.days_remaining
        return self.average_burn_rate >= required_burn_rate

    def schedule_variance(self) -> Optional[float]:
        """スケジュール偏差（日数）"""
        if self.average_burn_rate <= 0:
            return None

        projected_days = self.remaining_hours / self.average_burn_rate
        return projected_days - (self.days_remaining or 0)

    def scope_variance(self) -> float:
        """スコープ偏差（工数）"""
        return self.timeline.total_scope_change()
