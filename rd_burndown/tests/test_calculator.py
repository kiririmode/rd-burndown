"""Test cases for rd_burndown.core.calculator module."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from rd_burndown.core.calculator import (
    BurndownCalculator,
    CalculatorError,
    get_burndown_calculator,
)
from rd_burndown.core.models import ProjectTimeline


class TestCalculatorError:
    """Test CalculatorError exception."""

    def test_calculator_error_inherits_from_exception(self):
        """Test that CalculatorError inherits from Exception."""
        error = CalculatorError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"


class TestBurndownCalculator:
    """Test BurndownCalculator class."""

    @pytest.fixture
    def mock_data_manager(self):
        """Create a mock data manager."""
        return Mock()

    @pytest.fixture
    def calculator(self):
        """Create a BurndownCalculator instance."""
        with patch("rd_burndown.core.calculator.get_data_manager") as mock_get_dm:
            mock_dm = Mock()
            mock_get_dm.return_value = mock_dm
            return BurndownCalculator()

    @pytest.fixture
    def sample_timeline(self):
        """Create a sample ProjectTimeline for testing."""
        return ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            snapshots=[
                {
                    "date": "2024-01-01",
                    "total_estimated_hours": 100.0,
                    "remaining_hours": 100.0,
                    "completed_hours": 0.0,
                    "completed_ticket_count": 0,
                },
                {
                    "date": "2024-01-15",
                    "total_estimated_hours": 100.0,
                    "remaining_hours": 50.0,
                    "completed_hours": 50.0,
                    "completed_ticket_count": 5,
                },
                {
                    "date": "2024-01-31",
                    "total_estimated_hours": 100.0,
                    "remaining_hours": 0.0,
                    "completed_hours": 100.0,
                    "completed_ticket_count": 10,
                },
            ],
            scope_changes=[],
        )

    def test_init(self):
        """Test BurndownCalculator initialization."""
        with patch("rd_burndown.core.calculator.get_data_manager") as mock_get_dm:
            mock_dm = Mock()
            mock_get_dm.return_value = mock_dm
            calculator = BurndownCalculator()
            assert calculator.data_manager == mock_dm

    def test_calculate_project_timeline_success(self, calculator):
        """Test successful project timeline calculation."""
        # Setup mock data
        timeline_data = {
            "project": {
                "name": "Test Project",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
            "snapshots": [
                {
                    "date": "2024-01-01",
                    "total_estimated_hours": 100.0,
                    "remaining_hours": 100.0,
                    "completed_hours": 0.0,
                    "completed_ticket_count": 0,
                }
            ],
            "scope_changes": [],
        }

        calculator.data_manager.get_project_timeline.return_value = timeline_data

        result = calculator.calculate_project_timeline(1)

        assert isinstance(result, ProjectTimeline)
        assert result.project_id == 1
        assert result.project_name == "Test Project"

    def test_calculate_project_timeline_not_found(self, calculator):
        """Test project timeline calculation when project not found."""
        calculator.data_manager.get_project_timeline.return_value = None

        with pytest.raises(CalculatorError, match="Project 1 not found"):
            calculator.calculate_project_timeline(1)

    def test_calculate_project_timeline_data_manager_error(self, calculator):
        """Test project timeline calculation when data manager raises error."""
        calculator.data_manager.get_project_timeline.side_effect = Exception("DB error")

        with pytest.raises(
            CalculatorError, match="Failed to calculate project timeline"
        ):
            calculator.calculate_project_timeline(1)

    def test_calculate_ideal_line_success(self, calculator, sample_timeline):
        """Test successful ideal line calculation."""
        result = calculator.calculate_ideal_line(sample_timeline)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(point, tuple) and len(point) == 2 for point in result)
        # First point should have initial hours
        assert result[0][1] == 100.0
        # Last point should be close to 0 hours (floating point precision)
        assert abs(result[-1][1]) < 0.1

    def test_calculate_ideal_line_empty_snapshots(self, calculator):
        """Test ideal line calculation with empty snapshots."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            snapshots=[],
            scope_changes=[],
        )

        result = calculator.calculate_ideal_line(timeline)
        assert result == []

    def test_calculate_ideal_line_exclude_weekends(self, calculator, sample_timeline):
        """Test ideal line calculation excluding weekends."""
        result = calculator.calculate_ideal_line(sample_timeline, exclude_weekends=True)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_remaining_hours_for_date_success(self, calculator, sample_timeline):
        """指定日の残工数取得 - 成功"""
        target_date = date(2024, 1, 15)
        result = calculator._get_remaining_hours_for_date(sample_timeline, target_date)
        assert result == 50.0

    def test_get_remaining_hours_for_date_not_found(self, calculator, sample_timeline):
        """指定日の残工数取得 - データなし"""
        target_date = date(2024, 1, 20)  # 存在しない日付
        result = calculator._get_remaining_hours_for_date(sample_timeline, target_date)
        assert result is None

    def test_calculate_ideal_line_with_start_from_date(
        self, calculator, sample_timeline
    ):
        """理想線計算 - 指定日から開始"""
        start_from_date = date(2024, 1, 15)  # この日の残工数は50.0
        result = calculator.calculate_ideal_line(
            sample_timeline, start_from_date=start_from_date
        )

        # 理想線が指定日から開始されることを確認
        assert len(result) > 0
        assert result[0][0] == start_from_date
        assert result[0][1] == 50.0  # 指定日の残工数から開始  # 指定日の残工数から開始

    def test_calculate_ideal_line_with_start_from_date_not_found(
        self, calculator, sample_timeline
    ):
        """理想線計算 - 指定日のデータなし（初期工数にフォールバック）"""
        start_from_date = date(2024, 1, 20)  # 存在しない日付
        result = calculator.calculate_ideal_line(
            sample_timeline, start_from_date=start_from_date
        )

        # プロジェクト開始日から開始される（フォールバック）
        assert len(result) > 0
        assert result[0][0] == sample_timeline.start_date
        assert result[0][1] == 100.0  # 初期総工数から開始  # 初期総工数から開始

    def test_calculate_actual_line_success(self, calculator, sample_timeline):
        """Test successful actual line calculation."""
        result = calculator.calculate_actual_line(sample_timeline)

        assert isinstance(result, list)
        assert len(result) == 3  # Same as number of snapshots
        assert all(isinstance(point, tuple) and len(point) == 2 for point in result)
        # Verify data extraction from snapshots
        assert result[0] == (date(2024, 1, 1), 100.0)
        assert result[1] == (date(2024, 1, 15), 50.0)
        assert result[2] == (date(2024, 1, 31), 0.0)

    def test_calculate_dynamic_ideal_line_success(self, calculator, sample_timeline):
        """Test successful dynamic ideal line calculation."""
        result = calculator.calculate_dynamic_ideal_line(sample_timeline)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(point, tuple) and len(point) == 2 for point in result)

    def test_calculate_scope_trend_line_success(self, calculator, sample_timeline):
        """Test successful scope trend line calculation."""
        result = calculator.calculate_scope_trend_line(sample_timeline)

        assert isinstance(result, list)
        assert len(result) == 3  # Same as number of snapshots
        assert all(isinstance(point, tuple) and len(point) == 2 for point in result)
        # Verify total hours from snapshots
        assert result[0] == (date(2024, 1, 1), 100.0)
        assert result[1] == (date(2024, 1, 15), 100.0)
        assert result[2] == (date(2024, 1, 31), 100.0)

    def test_calculate_burn_rate_success(self, calculator, sample_timeline):
        """Test successful burn rate calculation."""
        result = calculator.calculate_burn_rate(sample_timeline, days=3)

        assert isinstance(result, float)
        assert result >= 0

    def test_calculate_burn_rate_insufficient_data(self, calculator):
        """Test burn rate calculation with insufficient data."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            snapshots=[
                {
                    "date": "2024-01-01",
                    "remaining_hours": 100.0,
                }
            ],
            scope_changes=[],
        )

        result = calculator.calculate_burn_rate(timeline)
        assert result == 0.0

    def test_calculate_velocity_success(self, calculator, sample_timeline):
        """Test successful velocity calculation."""
        result = calculator.calculate_velocity(sample_timeline, days=30)

        assert isinstance(result, dict)
        assert "velocity" in result
        assert "tickets_completed" in result
        assert "hours_completed" in result
        assert "period_days" in result

    def test_calculate_completion_forecast_success(self, calculator, sample_timeline):
        """Test successful completion forecast calculation."""
        result = calculator.calculate_completion_forecast(sample_timeline)

        assert isinstance(result, dict)
        assert "forecast_date" in result
        assert "days_remaining" in result
        assert "confidence" in result

    def test_calculate_completion_forecast_already_completed(self, calculator):
        """Test completion forecast when project is already completed."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            snapshots=[
                {
                    "date": "2024-01-05",
                    "remaining_hours": 0.0,
                    "completed_hours": 100.0,
                }
            ],
            scope_changes=[],
        )

        result = calculator.calculate_completion_forecast(timeline)

        assert result["forecast_date"] == date(2024, 1, 5)
        assert result["days_remaining"] == 0
        assert result["confidence"] == "high"

    def test_get_project_start_date_from_project(self, calculator):
        """Test project start date retrieval from project data."""
        project_data = {"start_date": "2024-01-01"}
        snapshots = []

        result = calculator._get_project_start_date(project_data, snapshots)
        assert result == date(2024, 1, 1)

    def test_get_project_start_date_from_snapshots(self, calculator):
        """Test project start date retrieval from snapshots."""
        project_data = {}
        snapshots = [{"date": "2024-01-02"}]

        result = calculator._get_project_start_date(project_data, snapshots)
        assert result == date(2024, 1, 2)

    def test_get_project_start_date_fallback_today(self, calculator):
        """Test project start date fallback to today."""
        project_data = {}
        snapshots = []

        result = calculator._get_project_start_date(project_data, snapshots)
        # Should return today's date as fallback
        assert isinstance(result, date)

    def test_get_project_end_date_success(self, calculator):
        """Test successful project end date retrieval."""
        project_data = {"end_date": "2024-01-31"}

        result = calculator._get_project_end_date(project_data)
        assert result == date(2024, 1, 31)

    def test_get_project_end_date_none(self, calculator):
        """Test project end date when not specified."""
        project_data = {}

        result = calculator._get_project_end_date(project_data)
        assert result is None


class TestGetBurndownCalculator:
    """Test get_burndown_calculator factory function."""

    def test_get_burndown_calculator_success(self):
        """Test successful burndown calculator creation."""
        with patch(
            "rd_burndown.core.calculator.get_data_manager"
        ) as mock_get_data_manager:
            mock_data_manager = Mock()
            mock_get_data_manager.return_value = mock_data_manager

            result = get_burndown_calculator()

            assert isinstance(result, BurndownCalculator)

    def test_get_burndown_calculator_with_mock_error(self):
        """Test burndown calculator creation with mock error."""
        # This tests that the function can handle initialization
        result = get_burndown_calculator()
        assert isinstance(result, BurndownCalculator)
