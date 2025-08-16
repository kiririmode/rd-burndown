"""チャートCLIコマンドのテスト"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from rd_burndown.cli.chart import chart


class TestChartCommands:
    """チャートコマンドのテスト"""

    def test_chart_group_help(self):
        """チャートグループのヘルプテスト"""
        runner = CliRunner()
        result = runner.invoke(chart, ["--help"])
        assert result.exit_code == 0
        assert "チャート生成コマンド" in result.output

    @patch("rd_burndown.cli.chart.get_chart_generator")
    def test_burndown_chart_generate(self, mock_get_generator):
        """バーンダウンチャート生成のテスト"""
        mock_generator = Mock()
        mock_generator.generate_burndown_chart.return_value = "chart.png"
        mock_get_generator.return_value = mock_generator

        runner = CliRunner()
        result = runner.invoke(
            chart, ["burndown", "1", "--output", "test.png"], obj={"verbose": False}
        )
        assert result.exit_code == 0

    @patch("rd_burndown.cli.chart.get_chart_generator")
    def test_burndown_chart_error(self, mock_get_generator):
        """バーンダウンチャート生成エラーのテスト"""
        mock_generator = Mock()
        mock_generator.generate_burndown_chart.side_effect = Exception("Chart error")
        mock_get_generator.return_value = mock_generator

        runner = CliRunner()
        result = runner.invoke(
            chart, ["burndown", "1", "--output", "test.png"], obj={"verbose": False}
        )
        assert result.exit_code == 1

    @patch("rd_burndown.cli.chart.get_chart_generator")
    def test_scope_chart_generate(self, mock_get_generator):
        """スコープチャート生成のテスト"""
        mock_generator = Mock()
        mock_generator.generate_scope_chart.return_value = "scope.png"
        mock_get_generator.return_value = mock_generator

        runner = CliRunner()
        result = runner.invoke(
            chart, ["scope", "1", "--output", "scope.png"], obj={"verbose": False}
        )
        assert result.exit_code == 0

    @patch("rd_burndown.cli.chart.get_chart_generator")
    def test_scope_chart_error(self, mock_get_generator):
        """スコープチャート生成エラーのテスト"""
        mock_generator = Mock()
        mock_generator.generate_scope_chart.side_effect = Exception("Scope error")
        mock_get_generator.return_value = mock_generator

        runner = CliRunner()
        result = runner.invoke(
            chart, ["scope", "1", "--output", "scope.png"], obj={"verbose": False}
        )
        assert result.exit_code == 1

    @patch("rd_burndown.cli.chart.get_chart_generator")
    def test_combined_chart_generate(self, mock_get_generator):
        """統合チャート生成のテスト"""
        mock_generator = Mock()
        mock_generator.generate_combined_chart.return_value = "combined.png"
        mock_get_generator.return_value = mock_generator

        runner = CliRunner()
        result = runner.invoke(
            chart, ["combined", "1", "--output", "combined.png"], obj={"verbose": False}
        )
        assert result.exit_code == 0


def add_chart_commands(cli_group):
    """チャートコマンドをCLIに追加"""
    cli_group.add_command(chart)