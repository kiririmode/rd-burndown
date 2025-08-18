"""バーンダウン計算エンジン"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

from rd_burndown.core.data_manager import get_data_manager
from rd_burndown.core.models import ProjectTimeline
from rd_burndown.utils.date_utils import get_business_days_between

logger = logging.getLogger(__name__)


class CalculatorError(Exception):
    """計算エラー"""


class BurndownCalculator:
    """バーンダウン計算エンジン"""

    def __init__(self):
        """初期化"""
        self.data_manager = get_data_manager()

    def calculate_project_timeline(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> ProjectTimeline:
        """
        プロジェクトの時系列データを計算

        Args:
            project_id: プロジェクトID
            start_date: 開始日（Noneの場合はプロジェクト開始日）
            end_date: 終了日（Noneの場合は現在日）

        Returns:
            ProjectTimeline: プロジェクト時系列データ
        """
        logger.info(f"Calculating project timeline for project {project_id}")

        try:
            # プロジェクトデータの取得
            timeline_data = self.data_manager.get_project_timeline(project_id)
            if not timeline_data:
                raise CalculatorError(f"Project {project_id} not found")

            project_data = timeline_data["project"]
            snapshots = timeline_data["snapshots"]
            scope_changes = timeline_data["scope_changes"]

            # 日付範囲の決定
            if start_date is None:
                start_date = self._get_project_start_date(project_data, snapshots)
            if end_date is None:
                end_date = date.today()

            # 指定範囲のスナップショットをフィルタリング
            filtered_snapshots = [
                snapshot
                for snapshot in snapshots
                if start_date
                <= datetime.fromisoformat(snapshot["date"]).date()
                <= end_date
            ]

            # 指定範囲のスコープ変更をフィルタリング
            filtered_scope_changes = [
                change
                for change in scope_changes
                if start_date
                <= datetime.fromisoformat(change["date"]).date()
                <= end_date
            ]

            # ProjectTimelineオブジェクトの作成
            return ProjectTimeline(
                project_id=project_id,
                project_name=project_data["name"],
                start_date=start_date,
                end_date=self._get_project_end_date(project_data),
                snapshots=filtered_snapshots,
                scope_changes=filtered_scope_changes,
            )

        except Exception as e:
            logger.error(f"Failed to calculate project timeline for {project_id}: {e}")
            raise CalculatorError(f"Failed to calculate project timeline: {e}") from e

    def calculate_ideal_line(
        self,
        timeline: ProjectTimeline,
        exclude_weekends: bool = False,
        start_from_date: Optional[date] = None,
    ) -> list[tuple[date, float]]:
        """
        理想線の計算

        Args:
            timeline: プロジェクト時系列データ
            exclude_weekends: 週末を除外するか
            start_from_date: 理想線を開始する日付。指定された場合、
                           その日の残工数から理想線を開始する

        Returns:
            理想線データ（日付, 残り工数）のリスト
        """
        if not timeline.snapshots:
            return []

        # 理想線の開始点を決定
        if start_from_date is not None:
            # 指定された日付の残工数を取得
            start_hours = self._get_remaining_hours_for_date(timeline, start_from_date)
            if start_hours is None:
                # 指定された日付のデータがない場合、エラーまたは警告
                logger.warning(
                    f"No data found for date {start_from_date}, using initial hours"
                )
                start_hours = timeline.snapshots[0]["total_estimated_hours"]
                start_date = timeline.start_date
            else:
                start_date = start_from_date
        else:
            # 従来通り初期総工数から開始
            start_hours = timeline.snapshots[0]["total_estimated_hours"]
            start_date = timeline.start_date

        # プロジェクト期間の計算
        end_date = timeline.end_date or date.today()

        if exclude_weekends:
            total_days = get_business_days_between(start_date, end_date)
        else:
            total_days = (end_date - start_date).days

        if total_days <= 0:
            return [(start_date, start_hours), (end_date, 0.0)]

        # 1日あたりの理想的な工数減少量
        daily_burn_rate = start_hours / total_days

        # 理想線の計算
        ideal_line = []
        current_date = start_date
        current_hours = start_hours

        while current_date <= end_date:
            ideal_line.append((current_date, max(0.0, current_hours)))

            # 次の日へ
            current_date += timedelta(days=1)
            if not exclude_weekends or current_date.weekday() < 5:  # 平日のみ減少
                current_hours -= daily_burn_rate

        return ideal_line

    def calculate_actual_line(
        self, timeline: ProjectTimeline
    ) -> list[tuple[date, float]]:
        """
        実際線の計算

        Args:
            timeline: プロジェクト時系列データ

        Returns:
            実際線データ（日付, 残り工数）のリスト
        """
        actual_line = []

        for snapshot in timeline.snapshots:
            snapshot_date = datetime.fromisoformat(snapshot["date"]).date()
            remaining_hours = snapshot["remaining_hours"]
            actual_line.append((snapshot_date, remaining_hours))

        return actual_line

    def calculate_dynamic_ideal_line(
        self, timeline: ProjectTimeline, exclude_weekends: bool = False
    ) -> list[tuple[date, float]]:
        """
        動的理想線の計算（スコープ変更を考慮）

        Args:
            timeline: プロジェクト時系列データ
            exclude_weekends: 週末を除外するか

        Returns:
            動的理想線データ（日付, 残り工数）のリスト
        """
        if not timeline.snapshots:
            return []

        # スコープ変更データの準備
        scope_changes_by_date = self._prepare_scope_changes_by_date(timeline)

        # 初期値設定
        current_date = timeline.start_date
        end_date = timeline.end_date or date.today()
        current_total_hours = timeline.snapshots[0]["total_estimated_hours"]

        # 動的理想線を日毎に計算
        return self._calculate_daily_dynamic_ideal(
            timeline,
            current_date,
            end_date,
            current_total_hours,
            scope_changes_by_date,
            exclude_weekends,
        )

    def _prepare_scope_changes_by_date(self, timeline: ProjectTimeline) -> dict:
        """日毎のスコープ変更を集計"""
        scope_changes_by_date = {}
        for change in timeline.scope_changes:
            change_date = datetime.fromisoformat(change["date"]).date()
            if change_date not in scope_changes_by_date:
                scope_changes_by_date[change_date] = 0.0
            scope_changes_by_date[change_date] += change["hours_delta"]
        return scope_changes_by_date

    def _calculate_daily_dynamic_ideal(
        self,
        timeline: ProjectTimeline,
        start_date: date,
        end_date: date,
        initial_total_hours: float,
        scope_changes_by_date: dict,
        exclude_weekends: bool,
    ) -> list[tuple[date, float]]:
        """日毎の動的理想線を計算"""
        dynamic_line = []
        current_date = start_date
        current_total_hours = initial_total_hours

        while current_date <= end_date:
            # スコープ変更を適用
            current_total_hours += scope_changes_by_date.get(current_date, 0.0)

            # 残り工数を計算
            remaining_hours = self._calculate_dynamic_remaining_hours(
                timeline, current_date, end_date, current_total_hours, exclude_weekends
            )

            dynamic_line.append((current_date, max(0.0, remaining_hours)))
            current_date += timedelta(days=1)

        return dynamic_line

    def _calculate_dynamic_remaining_hours(
        self,
        timeline: ProjectTimeline,
        current_date: date,
        end_date: date,
        current_total_hours: float,
        exclude_weekends: bool,
    ) -> float:
        """指定日の動的理想残り工数を計算"""
        # 残り日数を計算
        if exclude_weekends:
            remaining_days = get_business_days_between(current_date, end_date)
        else:
            remaining_days = (end_date - current_date).days

        if remaining_days <= 0:
            return 0.0

        # 完了工数を取得
        completed_hours = self._get_completed_hours_for_date(timeline, current_date)

        # 残り工数を計算
        return current_total_hours - completed_hours

    def _get_completed_hours_for_date(
        self, timeline: ProjectTimeline, target_date: date
    ) -> float:
        """指定日の完了工数を取得"""
        for snapshot in timeline.snapshots:
            snapshot_date = datetime.fromisoformat(snapshot["date"]).date()
            if snapshot_date == target_date:
                return snapshot["completed_hours"]
        return 0.0

    def _get_remaining_hours_for_date(
        self, timeline: ProjectTimeline, target_date: date
    ) -> Optional[float]:
        """
        指定した日の残工数を取得

        Args:
            timeline: プロジェクト時系列データ
            target_date: 対象日

        Returns:
            指定した日の残工数。該当日のデータがない場合はNone
        """
        for snapshot in timeline.snapshots:
            snapshot_date = datetime.fromisoformat(snapshot["date"]).date()
            if snapshot_date == target_date:
                return snapshot["remaining_hours"]
        return None

    def calculate_scope_trend_line(
        self, timeline: ProjectTimeline
    ) -> list[tuple[date, float]]:
        """
        総工数推移線の計算

        Args:
            timeline: プロジェクト時系列データ

        Returns:
            総工数推移線データ（日付, 総工数）のリスト
        """
        scope_trend = []

        for snapshot in timeline.snapshots:
            snapshot_date = datetime.fromisoformat(snapshot["date"]).date()
            total_hours = snapshot["total_estimated_hours"]
            scope_trend.append((snapshot_date, total_hours))

        return scope_trend

    def calculate_burn_rate(self, timeline: ProjectTimeline, days: int = 7) -> float:
        """
        バーンレートの計算

        Args:
            timeline: プロジェクト時系列データ
            days: 計算対象期間（日数）

        Returns:
            バーンレート（1日あたりの平均工数消化）
        """
        if len(timeline.snapshots) < 2:
            return 0.0

        # 最新のN日間のデータを取得
        recent_snapshots = (
            timeline.snapshots[-days:]
            if len(timeline.snapshots) >= days
            else timeline.snapshots
        )

        if len(recent_snapshots) < 2:
            return 0.0

        # 期間の開始と終了での工数差を計算
        start_snapshot = recent_snapshots[0]
        end_snapshot = recent_snapshots[-1]

        start_remaining = start_snapshot["remaining_hours"]
        end_remaining = end_snapshot["remaining_hours"]

        burned_hours = start_remaining - end_remaining
        actual_days = len(recent_snapshots) - 1

        return burned_hours / actual_days if actual_days > 0 else 0.0

    def calculate_velocity(
        self, timeline: ProjectTimeline, days: int = 14
    ) -> dict[str, float]:
        """
        ベロシティの計算

        Args:
            timeline: プロジェクト時系列データ
            days: 計算対象期間（日数）

        Returns:
            ベロシティ情報
        """
        if len(timeline.snapshots) < 2:
            return {"velocity": 0.0, "tickets_completed": 0, "hours_completed": 0.0}

        # 最新のN日間のデータを取得
        recent_snapshots = (
            timeline.snapshots[-days:]
            if len(timeline.snapshots) >= days
            else timeline.snapshots
        )

        if len(recent_snapshots) < 2:
            return {"velocity": 0.0, "tickets_completed": 0, "hours_completed": 0.0}

        # 期間の開始と終了での完了工数・チケット数の差を計算
        start_snapshot = recent_snapshots[0]
        end_snapshot = recent_snapshots[-1]

        completed_hours_delta = (
            end_snapshot["completed_hours"] - start_snapshot["completed_hours"]
        )
        completed_tickets_delta = (
            end_snapshot["completed_ticket_count"]
            - start_snapshot["completed_ticket_count"]
        )

        actual_days = len(recent_snapshots) - 1
        velocity = completed_hours_delta / actual_days if actual_days > 0 else 0.0

        return {
            "velocity": velocity,
            "tickets_completed": completed_tickets_delta,
            "hours_completed": completed_hours_delta,
            "period_days": actual_days,
        }

    def calculate_completion_forecast(
        self, timeline: ProjectTimeline, velocity_days: int = 14
    ) -> dict[str, Any]:
        """
        完了予測の計算

        Args:
            timeline: プロジェクト時系列データ
            velocity_days: ベロシティ計算期間

        Returns:
            完了予測情報
        """
        if not timeline.snapshots:
            return {"forecast_date": None, "days_remaining": None, "confidence": "low"}

        # 現在の残り工数
        latest_snapshot = timeline.snapshots[-1]
        remaining_hours = latest_snapshot["remaining_hours"]

        if remaining_hours <= 0:
            return {
                "forecast_date": datetime.fromisoformat(latest_snapshot["date"]).date(),
                "days_remaining": 0,
                "confidence": "high",
            }

        # 現在のベロシティ
        velocity_info = self.calculate_velocity(timeline, velocity_days)
        velocity = velocity_info["velocity"]

        if velocity <= 0:
            return {"forecast_date": None, "days_remaining": None, "confidence": "low"}

        # 予測計算
        days_needed = remaining_hours / velocity
        latest_date = datetime.fromisoformat(latest_snapshot["date"]).date()
        forecast_date = latest_date + timedelta(days=int(days_needed))

        # 信頼度の計算（ベロシティの安定性に基づく）
        burn_rate = self.calculate_burn_rate(timeline, velocity_days)
        confidence = (
            "high"
            if burn_rate > 0 and velocity > 0
            else "medium"
            if velocity > 0
            else "low"
        )

        return {
            "forecast_date": forecast_date,
            "days_remaining": int(days_needed),
            "confidence": confidence,
            "current_velocity": velocity,
            "remaining_hours": remaining_hours,
        }

    def _get_project_start_date(
        self, project_data: dict[str, Any], snapshots: list[dict[str, Any]]
    ) -> date:
        """プロジェクト開始日の取得"""
        if project_data.get("start_date"):
            return datetime.fromisoformat(project_data["start_date"]).date()
        if snapshots:
            return datetime.fromisoformat(snapshots[0]["date"]).date()
        return date.today()

    def _get_project_end_date(self, project_data: dict[str, Any]) -> Optional[date]:
        """プロジェクト終了日の取得"""
        if project_data.get("end_date"):
            return datetime.fromisoformat(project_data["end_date"]).date()
        return None


def get_burndown_calculator() -> BurndownCalculator:
    """
    バーンダウン計算機の取得

    Returns:
        BurndownCalculator: バーンダウン計算機インスタンス
    """
    return BurndownCalculator()
