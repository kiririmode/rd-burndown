"""データモデルのテスト"""

from datetime import date, datetime
from typing import Any

from rd_burndown.core.models import (
    DailySnapshot,
    ProjectSummary,
    ProjectTimeline,
    RedmineProject,
    ScopeChange,
    TicketData,
)


class TestTicketData:
    """TicketData のテスト"""

    def create_sample_ticket(self, **kwargs) -> TicketData:
        """サンプルチケット作成"""
        defaults = {
            "id": 1,
            "subject": "テストチケット",
            "estimated_hours": 8.0,
            "created_on": datetime(2024, 1, 1, 9, 0, 0),
            "updated_on": datetime(2024, 1, 5, 17, 0, 0),
            "status_id": 1,
            "status_name": "新規",
            "assigned_to_id": 100,
            "assigned_to_name": "山田太郎",
            "project_id": 1,
            "version_id": 1,
            "version_name": "v1.0.0",
            "custom_fields": {},
        }
        defaults.update(kwargs)
        return TicketData(**defaults)

    def test_create_ticket(self):
        """チケット作成のテスト"""
        ticket = self.create_sample_ticket()

        assert ticket.id == 1
        assert ticket.subject == "テストチケット"
        assert ticket.estimated_hours == 8.0
        assert ticket.status_id == 1
        assert ticket.project_id == 1

    def test_is_completed_true(self):
        """完了状態判定（完了）のテスト"""
        # 完了ステータスID: 3, 5, 6
        for status_id in [3, 5, 6]:
            ticket = self.create_sample_ticket(status_id=status_id)
            assert ticket.is_completed() is True

    def test_is_completed_false(self):
        """完了状態判定（未完了）のテスト"""
        # 未完了ステータスID
        for status_id in [1, 2, 4, 7]:
            ticket = self.create_sample_ticket(status_id=status_id)
            assert ticket.is_completed() is False

    def test_completion_date_completed(self):
        """完了日取得（完了）のテスト"""
        ticket = self.create_sample_ticket(status_id=3)  # 完了状態
        completion_date = ticket.completion_date()

        assert completion_date == ticket.updated_on

    def test_completion_date_not_completed(self):
        """完了日取得（未完了）のテスト"""
        ticket = self.create_sample_ticket(status_id=1)  # 未完了状態
        completion_date = ticket.completion_date()

        assert completion_date is None

    def test_estimated_hours_safe_with_value(self):
        """安全な予定工数取得（値あり）のテスト"""
        ticket = self.create_sample_ticket(estimated_hours=12.5)
        assert ticket.estimated_hours_safe() == 12.5

    def test_estimated_hours_safe_with_none(self):
        """安全な予定工数取得（None）のテスト"""
        ticket = self.create_sample_ticket(estimated_hours=None)
        assert ticket.estimated_hours_safe() == 0.0

    def test_custom_fields(self):
        """カスタムフィールドのテスト"""
        custom_fields = {"priority": "高", "category": "機能"}
        ticket = self.create_sample_ticket(custom_fields=custom_fields)

        assert ticket.custom_fields["priority"] == "高"
        assert ticket.custom_fields["category"] == "機能"


class TestDailySnapshot:
    """DailySnapshot のテスト"""

    def create_sample_snapshot(self, **kwargs) -> DailySnapshot:
        """サンプルスナップショット作成"""
        defaults = {
            "date": date(2024, 1, 15),
            "project_id": 1,
            "total_estimated_hours": 100.0,
            "completed_hours": 30.0,
            "remaining_hours": 70.0,
            "new_tickets_hours": 5.0,
            "changed_hours": 2.0,
            "deleted_hours": 1.0,
            "active_ticket_count": 10,
            "completed_ticket_count": 3,
        }
        defaults.update(kwargs)
        return DailySnapshot(**defaults)

    def test_create_snapshot(self):
        """スナップショット作成のテスト"""
        snapshot = self.create_sample_snapshot()

        assert snapshot.date == date(2024, 1, 15)
        assert snapshot.project_id == 1
        assert snapshot.total_estimated_hours == 100.0
        assert snapshot.completed_hours == 30.0

    def test_burn_rate(self):
        """バーンレート計算のテスト"""
        snapshot = self.create_sample_snapshot(completed_hours=25.0)
        assert snapshot.burn_rate() == 25.0

    def test_scope_change(self):
        """スコープ変更量計算のテスト"""
        snapshot = self.create_sample_snapshot(
            new_tickets_hours=10.0, changed_hours=5.0, deleted_hours=2.0
        )
        # 10 + 5 - 2 = 13
        assert snapshot.scope_change() == 13.0

    def test_scope_change_negative(self):
        """スコープ変更量計算（負の値）のテスト"""
        snapshot = self.create_sample_snapshot(
            new_tickets_hours=2.0, changed_hours=1.0, deleted_hours=5.0
        )
        # 2 + 1 - 5 = -2
        assert snapshot.scope_change() == -2.0

    def test_total_tickets(self):
        """総チケット数計算のテスト"""
        snapshot = self.create_sample_snapshot(
            active_ticket_count=15, completed_ticket_count=8
        )
        assert snapshot.total_tickets() == 23

    def test_completion_rate(self):
        """完了率計算のテスト"""
        snapshot = self.create_sample_snapshot(
            active_ticket_count=7, completed_ticket_count=3
        )
        # 3 / (7 + 3) * 100 = 30.0
        assert snapshot.completion_rate() == 30.0

    def test_completion_rate_no_tickets(self):
        """完了率計算（チケット0件）のテスト"""
        snapshot = self.create_sample_snapshot(
            active_ticket_count=0, completed_ticket_count=0
        )
        assert snapshot.completion_rate() == 0.0


class TestScopeChange:
    """ScopeChange のテスト"""

    def create_sample_scope_change(self, **kwargs) -> ScopeChange:
        """サンプルスコープ変更作成"""
        defaults = {
            "date": date(2024, 1, 20),
            "project_id": 1,
            "change_type": "added",
            "ticket_id": 123,
            "ticket_subject": "新機能追加",
            "hours_delta": 16.0,
            "old_hours": None,
            "new_hours": 16.0,
            "reason": "要件追加",
        }
        defaults.update(kwargs)
        return ScopeChange(**defaults)

    def test_create_scope_change(self):
        """スコープ変更作成のテスト"""
        change = self.create_sample_scope_change()

        assert change.date == date(2024, 1, 20)
        assert change.change_type == "added"
        assert change.hours_delta == 16.0
        assert change.reason == "要件追加"

    def test_impact_level_high(self):
        """影響度判定（高）のテスト"""
        change = self.create_sample_scope_change(hours_delta=50.0)
        assert change.impact_level() == "high"

    def test_impact_level_medium(self):
        """影響度判定（中）のテスト"""
        change = self.create_sample_scope_change(hours_delta=16.0)
        assert change.impact_level() == "medium"

    def test_impact_level_low(self):
        """影響度判定（低）のテスト"""
        change = self.create_sample_scope_change(hours_delta=4.0)
        assert change.impact_level() == "low"

    def test_impact_level_negative(self):
        """影響度判定（負の値）のテスト"""
        change = self.create_sample_scope_change(hours_delta=-20.0)
        assert change.impact_level() == "medium"  # 絶対値で判定

    def test_is_scope_increase(self):
        """スコープ増加判定のテスト"""
        change = self.create_sample_scope_change(hours_delta=10.0)
        assert change.is_scope_increase() is True

        change = self.create_sample_scope_change(hours_delta=-10.0)
        assert change.is_scope_increase() is False

    def test_is_scope_decrease(self):
        """スコープ減少判定のテスト"""
        change = self.create_sample_scope_change(hours_delta=-5.0)
        assert change.is_scope_decrease() is True

        change = self.create_sample_scope_change(hours_delta=5.0)
        assert change.is_scope_decrease() is False


class TestProjectTimeline:
    """ProjectTimeline のテスト"""

    def create_sample_timeline(self, **kwargs) -> ProjectTimeline:
        """サンプルタイムライン作成"""
        defaults = {
            "project_id": 1,
            "project_name": "テストプロジェクト",
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "snapshots": [],
            "scope_changes": [],
        }
        defaults.update(kwargs)
        return ProjectTimeline(**defaults)

    def create_sample_snapshots(self) -> list[dict[str, Any]]:
        """サンプルスナップショット群作成"""
        return [
            {
                "date": "2024-01-01",
                "project_id": 1,
                "total_estimated_hours": 100.0,
                "completed_hours": 0.0,
                "remaining_hours": 100.0,
                "new_tickets_hours": 0.0,
                "changed_hours": 0.0,
                "deleted_hours": 0.0,
                "active_ticket_count": 10,
                "completed_ticket_count": 0,
            },
            {
                "date": "2024-01-15",
                "project_id": 1,
                "total_estimated_hours": 105.0,
                "completed_hours": 30.0,
                "remaining_hours": 75.0,
                "new_tickets_hours": 5.0,
                "changed_hours": 0.0,
                "deleted_hours": 0.0,
                "active_ticket_count": 8,
                "completed_ticket_count": 2,
            },
            {
                "date": "2024-01-31",
                "project_id": 1,
                "total_estimated_hours": 105.0,
                "completed_hours": 105.0,
                "remaining_hours": 0.0,
                "new_tickets_hours": 0.0,
                "changed_hours": 0.0,
                "deleted_hours": 0.0,
                "active_ticket_count": 0,
                "completed_ticket_count": 10,
            },
        ]

    def test_create_timeline(self):
        """タイムライン作成のテスト"""
        timeline = self.create_sample_timeline()

        assert timeline.project_id == 1
        assert timeline.project_name == "テストプロジェクト"
        assert timeline.start_date == date(2024, 1, 1)
        assert timeline.end_date == date(2024, 1, 31)

    def test_ideal_line_empty_snapshots(self):
        """理想線計算（スナップショット空）のテスト"""
        timeline = self.create_sample_timeline()
        ideal_line = timeline.ideal_line()
        assert ideal_line == []

    def test_ideal_line_no_end_date(self):
        """理想線計算（終了日なし）のテスト"""
        timeline = self.create_sample_timeline(end_date=None)
        ideal_line = timeline.ideal_line()
        assert ideal_line == []

    def test_ideal_line_calculation(self):
        """理想線計算のテスト"""
        snapshots = self.create_sample_snapshots()
        timeline = self.create_sample_timeline(snapshots=snapshots)

        ideal_line = timeline.ideal_line()

        # 理想線は開始日から終了日まで線形減少
        assert len(ideal_line) > 0
        assert ideal_line[0][0] == date(2024, 1, 1)  # 開始日
        assert ideal_line[0][1] == 100.0  # 初期工数
        assert ideal_line[-1][0] == date(2024, 1, 31)  # 終了日
        assert abs(ideal_line[-1][1]) < 1e-10  # 最終工数（浮動小数点誤差考慮）

    def test_actual_line(self):
        """実際線計算のテスト"""
        snapshots = self.create_sample_snapshots()
        timeline = self.create_sample_timeline(snapshots=snapshots)

        actual_line = timeline.actual_line()

        assert len(actual_line) == 3
        assert actual_line[0] == (date(2024, 1, 1), 100.0)
        assert actual_line[1] == (date(2024, 1, 15), 75.0)
        assert actual_line[2] == (date(2024, 1, 31), 0.0)

    def test_scope_trend_line(self):
        """総工数推移線計算のテスト"""
        snapshots = self.create_sample_snapshots()
        timeline = self.create_sample_timeline(snapshots=snapshots)

        scope_line = timeline.scope_trend_line()

        assert len(scope_line) == 3
        assert scope_line[0] == (date(2024, 1, 1), 100.0)
        assert scope_line[1] == (date(2024, 1, 15), 105.0)  # 5時間追加
        assert scope_line[2] == (date(2024, 1, 31), 105.0)

    def test_get_snapshot_by_date_found(self):
        """指定日スナップショット取得（見つかる）のテスト"""
        snapshots = self.create_sample_snapshots()
        timeline = self.create_sample_timeline(snapshots=snapshots)

        snapshot = timeline.get_snapshot_by_date(date(2024, 1, 15))

        assert snapshot is not None
        assert snapshot["date"] == "2024-01-15"
        assert snapshot["remaining_hours"] == 75.0

    def test_get_snapshot_by_date_not_found(self):
        """指定日スナップショット取得（見つからない）のテスト"""
        snapshots = self.create_sample_snapshots()
        timeline = self.create_sample_timeline(snapshots=snapshots)

        snapshot = timeline.get_snapshot_by_date(date(2024, 2, 1))

        assert snapshot is None

    def test_total_scope_change(self):
        """総スコープ変更量のテスト"""
        scope_changes = [
            {
                "date": "2024-01-10",
                "project_id": 1,
                "change_type": "added",
                "ticket_id": 1,
                "ticket_subject": "追加1",
                "hours_delta": 8.0,
                "old_hours": None,
                "new_hours": 8.0,
                "reason": "要件追加",
            },
            {
                "date": "2024-01-20",
                "project_id": 1,
                "change_type": "removed",
                "ticket_id": 2,
                "ticket_subject": "削除1",
                "hours_delta": -4.0,
                "old_hours": 4.0,
                "new_hours": None,
                "reason": "要件削除",
            },
        ]

        timeline = self.create_sample_timeline(scope_changes=scope_changes)

        # 8.0 + (-4.0) = 4.0
        assert timeline.total_scope_change() == 4.0

    def test_current_status(self):
        """現在ステータス取得のテスト"""
        snapshots = self.create_sample_snapshots()
        timeline = self.create_sample_timeline(snapshots=snapshots)

        current = timeline.current_status()

        assert current is not None
        assert current["date"] == "2024-01-31"  # 最新のスナップショット

    def test_current_status_no_snapshots(self):
        """現在ステータス取得（スナップショットなし）のテスト"""
        timeline = self.create_sample_timeline()

        current = timeline.current_status()

        assert current is None


class TestRedmineProject:
    """RedmineProject のテスト"""

    def create_sample_project(self, **kwargs) -> RedmineProject:
        """サンプルプロジェクト作成"""
        defaults = {
            "id": 1,
            "name": "テストプロジェクト",
            "identifier": "test-project",
            "description": "テスト用のプロジェクトです",
            "status": 1,
            "created_on": datetime(2024, 1, 1, 9, 0, 0),
            "updated_on": datetime(2024, 1, 15, 17, 0, 0),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "versions": [
                {"id": 1, "name": "v1.0.0", "status": "open"},
                {"id": 2, "name": "v1.1.0", "status": "open"},
                {"id": 3, "name": "v0.9.0", "status": "closed"},
            ],
            "custom_fields": {"category": "開発"},
        }
        defaults.update(kwargs)
        return RedmineProject(**defaults)

    def test_create_project(self):
        """プロジェクト作成のテスト"""
        project = self.create_sample_project()

        assert project.id == 1
        assert project.name == "テストプロジェクト"
        assert project.identifier == "test-project"
        assert project.status == 1

    def test_active_versions(self):
        """アクティブバージョン取得のテスト"""
        project = self.create_sample_project()

        active_versions = project.active_versions()

        assert len(active_versions) == 2
        assert active_versions[0]["name"] == "v1.0.0"
        assert active_versions[1]["name"] == "v1.1.0"

    def test_is_active_true(self):
        """アクティブ判定（アクティブ）のテスト"""
        project = self.create_sample_project(status=1)
        assert project.is_active() is True

    def test_is_active_false(self):
        """アクティブ判定（非アクティブ）のテスト"""
        project = self.create_sample_project(status=5)
        assert project.is_active() is False

    def test_is_closed_true(self):
        """クローズ判定（クローズ）のテスト"""
        project = self.create_sample_project(status=5)
        assert project.is_closed() is True

    def test_is_closed_false(self):
        """クローズ判定（アクティブ）のテスト"""
        project = self.create_sample_project(status=1)
        assert project.is_closed() is False

    def test_get_version_by_id_found(self):
        """ID指定バージョン取得（見つかる）のテスト"""
        project = self.create_sample_project()

        version = project.get_version_by_id(2)

        assert version is not None
        assert version["id"] == 2
        assert version["name"] == "v1.1.0"

    def test_get_version_by_id_not_found(self):
        """ID指定バージョン取得（見つからない）のテスト"""
        project = self.create_sample_project()

        version = project.get_version_by_id(99)

        assert version is None


class TestProjectSummary:
    """ProjectSummary のテスト"""

    def create_sample_summary(self, **kwargs) -> ProjectSummary:
        """サンプルサマリー作成"""
        project = RedmineProject(
            id=1,
            name="テストプロジェクト",
            identifier="test",
            description="",
            status=1,
            created_on=datetime.now(),
            updated_on=datetime.now(),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            versions=[],
            custom_fields={},
        )

        timeline = ProjectTimeline(
            project_id=1,
            project_name="テストプロジェクト",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            snapshots=[],
            scope_changes=[],
        )

        defaults = {
            "project": project,
            "timeline": timeline,
            "total_tickets": 10,
            "completed_tickets": 4,
            "total_estimated_hours": 100.0,
            "completed_hours": 40.0,
            "remaining_hours": 60.0,
            "days_elapsed": 15,
            "days_remaining": 16,
            "completion_rate": 40.0,
            "average_burn_rate": 2.67,
            "estimated_completion_date": date(2024, 2, 15),
        }
        defaults.update(kwargs)
        return ProjectSummary(**defaults)

    def test_create_summary(self):
        """サマリー作成のテスト"""
        summary = self.create_sample_summary()

        assert summary.total_tickets == 10
        assert summary.completed_tickets == 4
        assert summary.completion_rate == 40.0

    def test_is_on_track_true(self):
        """予定通り進行判定（順調）のテスト"""
        summary = self.create_sample_summary(
            remaining_hours=60.0,
            days_remaining=20,
            average_burn_rate=4.0,  # 必要バーンレート3.0を上回る
        )

        assert summary.is_on_track() is True

    def test_is_on_track_false(self):
        """予定通り進行判定（遅延）のテスト"""
        summary = self.create_sample_summary(
            remaining_hours=60.0,
            days_remaining=20,
            average_burn_rate=2.0,  # 必要バーンレート3.0を下回る
        )

        assert summary.is_on_track() is False

    def test_is_on_track_no_days_remaining(self):
        """予定通り進行判定（残り日数なし）のテスト"""
        summary = self.create_sample_summary(
            remaining_hours=10.0, days_remaining=None, average_burn_rate=2.0
        )

        # 残り工数があるので遅延
        assert summary.is_on_track() is False

    def test_schedule_variance_positive(self):
        """スケジュール偏差（遅延）のテスト"""
        summary = self.create_sample_summary(
            remaining_hours=60.0, days_remaining=15, average_burn_rate=3.0
        )

        # 必要日数: 60 / 3 = 20日、残り日数: 15日 → 偏差: +5日
        variance = summary.schedule_variance()
        assert variance == 5.0

    def test_schedule_variance_negative(self):
        """スケジュール偏差（前倒し）のテスト"""
        summary = self.create_sample_summary(
            remaining_hours=60.0, days_remaining=25, average_burn_rate=3.0
        )

        # 必要日数: 60 / 3 = 20日、残り日数: 25日 → 偏差: -5日
        variance = summary.schedule_variance()
        assert variance == -5.0

    def test_schedule_variance_zero_burn_rate(self):
        """スケジュール偏差（バーンレート0）のテスト"""
        summary = self.create_sample_summary(
            remaining_hours=60.0, days_remaining=15, average_burn_rate=0.0
        )

        variance = summary.schedule_variance()
        assert variance is None

    def test_scope_variance(self):
        """スコープ偏差のテスト"""
        # スコープ変更のあるタイムライン作成
        timeline = ProjectTimeline(
            project_id=1,
            project_name="テスト",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            snapshots=[],
            scope_changes=[
                {
                    "date": "2024-01-10",
                    "project_id": 1,
                    "change_type": "added",
                    "ticket_id": 1,
                    "ticket_subject": "追加",
                    "hours_delta": 10.0,
                    "old_hours": None,
                    "new_hours": 10.0,
                    "reason": "要件追加",
                },
            ],
        )

        summary = self.create_sample_summary(timeline=timeline)

        assert summary.scope_variance() == 10.0
