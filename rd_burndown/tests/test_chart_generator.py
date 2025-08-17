"""Test cases for rd_burndown.core.chart_generator module."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rd_burndown.core.chart_generator import (
    ChartGenerator,
    ChartGeneratorError,
    get_chart_generator,
)
from rd_burndown.core.models import ProjectTimeline


class TestChartGeneratorError:
    """Test ChartGeneratorError exception."""

    def test_chart_generator_error_inherits_from_exception(self):
        """Test that ChartGeneratorError inherits from Exception."""
        error = ChartGeneratorError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"


class TestChartGenerator:
    """Test ChartGenerator class."""

    @pytest.fixture
    def chart_generator(self):
        """Create a ChartGenerator instance with mocked dependencies."""
        with (
            patch("rd_burndown.core.chart_generator.get_config_manager") as mock_get_cm,
            patch(
                "rd_burndown.core.chart_generator.get_burndown_calculator"
            ) as mock_get_calc,
            patch("matplotlib.pyplot.style.use"),
            patch("seaborn.set_palette"),
            patch("matplotlib.pyplot.rcParams"),
        ):
            # Setup config mock
            mock_config_manager = Mock()
            mock_config = Mock()
            mock_config.output.output_dir = "output"
            mock_config.output.default_dpi = 300
            mock_config.chart.font_size = 12
            mock_config_manager.load_config.return_value = mock_config

            # Setup calculator mock
            mock_calculator = Mock()

            mock_get_cm.return_value = mock_config_manager
            mock_get_calc.return_value = mock_calculator

            return ChartGenerator()

    def test_init_success(self):
        """Test successful ChartGenerator initialization."""
        with (
            patch("rd_burndown.core.chart_generator.get_config_manager") as mock_get_cm,
            patch(
                "rd_burndown.core.chart_generator.get_burndown_calculator"
            ) as mock_get_calc,
            patch("matplotlib.pyplot.style.use"),
            patch("seaborn.set_palette"),
            patch("matplotlib.font_manager"),
            patch("matplotlib.pyplot.rcParams"),
        ):
            mock_config_manager = Mock()
            mock_config = Mock()
            mock_config.chart.font_size = 12
            mock_config_manager.load_config.return_value = mock_config
            mock_get_cm.return_value = mock_config_manager
            mock_get_calc.return_value = Mock()

            cg = ChartGenerator()

            assert cg.config_manager == mock_config_manager
            assert cg.config == mock_config
            assert hasattr(cg, "_no_japanese_font")

    def test_generate_burndown_chart_success(self, chart_generator):
        """Test successful burndown chart generation."""
        # Mock timeline data
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[
                {"date": "2024-01-01", "remaining_hours": 100.0},
                {"date": "2024-01-02", "remaining_hours": 90.0},
            ],
            scope_changes=[],
        )

        chart_generator.calculator.calculate_project_timeline.return_value = timeline

        with patch.object(chart_generator, "_create_burndown_chart") as mock_create:
            mock_fig = Mock()
            mock_create.return_value = mock_fig

            with patch("pathlib.Path.mkdir"), patch("matplotlib.pyplot.close"):
                output_path = chart_generator.generate_burndown_chart(
                    project_id=1,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                )

                assert output_path is not None
                mock_create.assert_called_once()
                mock_fig.savefig.assert_called_once()

    def test_generate_burndown_chart_with_output_path(self, chart_generator):
        """Test burndown chart generation with specific output path."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[],
            scope_changes=[],
        )

        chart_generator.calculator.calculate_project_timeline.return_value = timeline

        with patch.object(chart_generator, "_create_burndown_chart") as mock_create:
            mock_fig = Mock()
            mock_create.return_value = mock_fig

            with patch("matplotlib.pyplot.close"):
                output_path = Path("custom_output.png")
                result_path = chart_generator.generate_burndown_chart(
                    project_id=1,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    output_path=output_path,
                )

                assert result_path == output_path
                mock_fig.savefig.assert_called_once()

    def test_generate_burndown_chart_calculation_error(self, chart_generator):
        """Test burndown chart generation with calculation error."""
        chart_generator.calculator.calculate_project_timeline.side_effect = Exception(
            "Calc error"
        )

        with pytest.raises(
            ChartGeneratorError, match="Failed to generate burndown chart"
        ):
            chart_generator.generate_burndown_chart(
                project_id=1, start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)
            )

    def test_generate_scope_chart_success(self, chart_generator):
        """Test successful scope chart generation."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[],
            scope_changes=[
                {"date": "2024-01-01", "hours_delta": 10.0, "change_type": "added"}
            ],
        )

        chart_generator.calculator.calculate_project_timeline.return_value = timeline

        with patch.object(chart_generator, "_create_scope_chart") as mock_create:
            mock_fig = Mock()
            mock_create.return_value = mock_fig

            with patch("pathlib.Path.mkdir"), patch("matplotlib.pyplot.close"):
                output_path = chart_generator.generate_scope_chart(
                    project_id=1,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                )

                assert output_path is not None
                mock_create.assert_called_once()
                mock_fig.savefig.assert_called_once()

    def test_generate_combined_chart_success(self, chart_generator):
        """Test successful combined chart generation."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[],
            scope_changes=[],
        )

        chart_generator.calculator.calculate_project_timeline.return_value = timeline

        with patch.object(chart_generator, "_create_combined_chart") as mock_create:
            mock_fig = Mock()
            mock_create.return_value = mock_fig

            with patch("pathlib.Path.mkdir"), patch("matplotlib.pyplot.close"):
                output_path = chart_generator.generate_combined_chart(
                    project_id=1,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                )

                assert output_path is not None
                mock_create.assert_called_once()
                mock_fig.savefig.assert_called_once()

    def test_create_burndown_chart_basic(self, chart_generator):
        """Test basic burndown chart creation."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[
                {"date": "2024-01-01", "remaining_hours": 100.0},
                {"date": "2024-01-02", "remaining_hours": 90.0},
            ],
            scope_changes=[],
        )

        # Mock calculator methods
        chart_generator.calculator.calculate_ideal_line.return_value = [
            (date(2024, 1, 1), 100.0),
            (date(2024, 12, 31), 0.0),
        ]
        chart_generator.calculator.calculate_actual_line.return_value = [
            (date(2024, 1, 1), 100.0),
            (date(2024, 1, 2), 90.0),
        ]

        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = Mock()
            mock_ax = Mock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            with patch.object(chart_generator, "_setup_chart_style"):
                fig = chart_generator._create_burndown_chart(timeline, 12, 8, 300)

                assert fig == mock_fig
                # The actual call divides width/height by dpi: (12/300, 8/300)
                mock_subplots.assert_called_once_with(
                    figsize=(12 / 300, 8 / 300), dpi=300
                )

    def test_create_scope_chart_basic(self, chart_generator):
        """Test basic scope chart creation."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[],
            scope_changes=[
                {"date": "2024-01-01", "hours_delta": 10.0, "change_type": "added"}
            ],
        )

        # Mock calculator method
        chart_generator.calculator.calculate_scope_trend_line.return_value = [
            (date(2024, 1, 1), 100.0),
            (date(2024, 1, 2), 110.0),
        ]

        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = Mock()
            mock_ax = Mock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            with patch.object(chart_generator, "_setup_chart_style"):
                fig = chart_generator._create_scope_chart(timeline, True, 12, 8)

                assert fig == mock_fig
                # The actual implementation divides by 100, not by dpi
                mock_subplots.assert_called_once_with(figsize=(12 / 100, 8 / 100))

    def test_create_combined_chart_basic(self, chart_generator):
        """Test basic combined chart creation."""
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[{"date": "2024-01-01", "remaining_hours": 100.0}],
            scope_changes=[
                {"date": "2024-01-01", "hours_delta": 10.0, "change_type": "added"}
            ],
        )

        # Mock calculator methods
        chart_generator.calculator.calculate_ideal_line.return_value = [
            (date(2024, 1, 1), 100.0),
            (date(2024, 12, 31), 0.0),
        ]
        chart_generator.calculator.calculate_actual_line.return_value = [
            (date(2024, 1, 1), 100.0)
        ]
        chart_generator.calculator.calculate_dynamic_ideal_line.return_value = [
            (date(2024, 1, 1), 100.0),
            (date(2024, 12, 31), 0.0),
        ]

        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = Mock()
            mock_ax = Mock()
            # Mock the ax.lines attribute to return an empty list for label checking
            mock_ax.lines = []
            mock_subplots.return_value = (mock_fig, mock_ax)

            with patch.object(chart_generator, "_setup_chart_style"):
                fig = chart_generator._create_combined_chart(timeline, 16, 10)

                assert fig == mock_fig
                # The actual implementation divides by 100
                mock_subplots.assert_called_once_with(figsize=(16 / 100, 10 / 100))

    def test_setup_chart_style(self, chart_generator):
        """Test chart style setup."""
        mock_ax = Mock()
        timeline = ProjectTimeline(
            project_id=1,
            project_name="Test Project",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            snapshots=[{"total_estimated_hours": 100.0}],
            scope_changes=[],
        )

        with patch("matplotlib.pyplot.setp"):
            chart_generator._setup_chart_style(
                mock_ax, timeline, "バーンダウンチャート"
            )

        mock_ax.set_title.assert_called_once()
        # The mock ax calls will vary based on _no_japanese_font flag
        mock_ax.set_xlabel.assert_called_once()
        mock_ax.set_ylabel.assert_called_once()
        mock_ax.grid.assert_called_once()


class TestGetChartGenerator:
    """Test get_chart_generator function."""

    def test_get_chart_generator_success(self):
        """Test successful chart generator retrieval."""
        with patch("rd_burndown.core.chart_generator.ChartGenerator") as mock_cg:
            mock_instance = Mock()
            mock_cg.return_value = mock_instance

            result = get_chart_generator()

            assert result == mock_instance
            mock_cg.assert_called_once()

    def test_get_chart_generator_error(self):
        """Test chart generator retrieval with error."""
        with patch("rd_burndown.core.chart_generator.ChartGenerator") as mock_cg:
            mock_cg.side_effect = Exception("Generator error")

            with pytest.raises(
                ChartGeneratorError, match="Failed to create chart generator"
            ):
                get_chart_generator()
