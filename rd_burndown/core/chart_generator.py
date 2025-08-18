"""チャート生成エンジン"""

import logging
from datetime import date
from pathlib import Path
from typing import Optional

# 日本語フォント対応は自動選択機能で実装
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, date2num
from matplotlib.figure import Figure

from rd_burndown.core.calculator import get_burndown_calculator
from rd_burndown.core.models import ProjectTimeline
from rd_burndown.utils.config import get_config_manager

logger = logging.getLogger(__name__)


class ChartGeneratorError(Exception):
    """チャート生成エラー"""


class ChartGenerator:
    """チャート生成エンジン"""

    def __init__(self):
        """初期化"""
        self.config_manager = get_config_manager()
        self.config = self.config_manager.load_config()
        self.calculator = get_burndown_calculator()
        self._no_japanese_font = False  # 初期化

        # matplotlib設定
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

        # フォント設定
        self._no_japanese_font = False
        try:
            import matplotlib.font_manager as fm

            # 利用可能なフォント名を取得
            available_fonts = [f.name for f in fm.fontManager.ttflist]
            logger.debug(f"Available fonts: {len(available_fonts)} fonts found")

            # 日本語対応フォントの優先順位リスト
            japanese_fonts = [
                "Noto Sans CJK JP",
                "Noto Sans JP",
                "Takao Gothic",
                "Takao Mincho",
                "Hiragino Sans",
                "Yu Gothic",
                "Meiryo",
                "MS Gothic",
                "SimHei",  # 中国語フォントも日本語文字をカバー
                "SimSun",
                "Arial Unicode MS",
                "Liberation Sans",  # Linuxで使用可能
                "DejaVu Sans",  # フォールバック
            ]

            # 利用可能な日本語フォントを探す
            selected_font = None
            for font in japanese_fonts:
                if font in available_fonts:
                    selected_font = font
                    break

            if selected_font:
                plt.rcParams["font.family"] = selected_font
                logger.info(f"Selected font: {selected_font}")
                # 実際に日本語文字が表示できるかテスト
                if selected_font not in ["Liberation Sans", "DejaVu Sans"]:
                    self._no_japanese_font = False
                else:
                    self._no_japanese_font = True
                    logger.info("Using English labels due to limited font support")
            else:
                # フォント選択に失敗した場合はフォールバック
                logger.warning(
                    "No suitable fonts found. Using default font with English labels."
                )
                plt.rcParams["font.family"] = "DejaVu Sans"
                self._no_japanese_font = True

            # Unicode minusを無効化
            plt.rcParams["axes.unicode_minus"] = False

        except Exception as e:
            logger.error(f"Failed to set font: {e}")
            plt.rcParams["font.family"] = "DejaVu Sans"
            plt.rcParams["axes.unicode_minus"] = False
            self._no_japanese_font = True

        plt.rcParams["font.size"] = self.config.chart.font_size

    def generate_burndown_chart(
        self,
        project_id: int,
        output_path: Optional[Path] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        width: int = 1200,
        height: int = 800,
        dpi: int = 300,
    ) -> Path:
        """
        標準バーンダウンチャート生成

        Args:
            project_id: プロジェクトID
            output_path: 出力パス
            start_date: 開始日
            end_date: 終了日
            width: 幅
            height: 高さ
            dpi: DPI

        Returns:
            出力ファイルパス
        """
        logger.info(f"Generating burndown chart for project {project_id}")

        try:
            # プロジェクトタイムライン取得
            timeline = self.calculator.calculate_project_timeline(
                project_id, start_date, end_date
            )

            # チャート作成
            fig = self._create_burndown_chart(timeline, width, height, dpi)

            # 出力パス決定
            if output_path is None:
                output_dir = Path(self.config.output.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"burndown_project_{project_id}.png"

            # 保存
            fig.savefig(
                output_path,
                dpi=dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            plt.close(fig)

            logger.info(f"Burndown chart saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate burndown chart: {e}")
            raise ChartGeneratorError(f"Failed to generate burndown chart: {e}") from e

    def generate_scope_chart(
        self,
        project_id: int,
        output_path: Optional[Path] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        show_changes: bool = True,
        width: int = 1200,
        height: int = 800,
    ) -> Path:
        """
        スコープ変更チャート生成

        Args:
            project_id: プロジェクトID
            output_path: 出力パス
            start_date: 開始日
            end_date: 終了日
            show_changes: 変更マーカー表示
            width: 幅
            height: 高さ

        Returns:
            出力ファイルパス
        """
        logger.info(f"Generating scope chart for project {project_id}")

        try:
            # プロジェクトタイムライン取得
            timeline = self.calculator.calculate_project_timeline(
                project_id, start_date, end_date
            )

            # チャート作成
            fig = self._create_scope_chart(timeline, show_changes, width, height)

            # 出力パス決定
            if output_path is None:
                output_dir = Path(self.config.output.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"scope_project_{project_id}.png"

            # 保存
            fig.savefig(
                output_path,
                dpi=self.config.output.default_dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            plt.close(fig)

            logger.info(f"Scope chart saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate scope chart: {e}")
            raise ChartGeneratorError(f"Failed to generate scope chart: {e}") from e

    def generate_combined_chart(
        self,
        project_id: int,
        output_path: Optional[Path] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        width: int = 1200,
        height: int = 800,
    ) -> Path:
        """
        統合チャート生成

        Args:
            project_id: プロジェクトID
            output_path: 出力パス
            start_date: 開始日
            end_date: 終了日
            width: 幅
            height: 高さ

        Returns:
            出力ファイルパス
        """
        logger.info(f"Generating combined chart for project {project_id}")

        try:
            # プロジェクトタイムライン取得
            timeline = self.calculator.calculate_project_timeline(
                project_id, start_date, end_date
            )

            # チャート作成
            fig = self._create_combined_chart(timeline, width, height)

            # 出力パス決定
            if output_path is None:
                output_dir = Path(self.config.output.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"combined_project_{project_id}.png"

            # 保存
            fig.savefig(
                output_path,
                dpi=self.config.output.default_dpi,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            plt.close(fig)

            logger.info(f"Combined chart saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate combined chart: {e}")
            raise ChartGeneratorError(f"Failed to generate combined chart: {e}") from e

    def _create_burndown_chart(
        self, timeline: ProjectTimeline, width: int, height: int, dpi: int
    ) -> Figure:
        """標準バーンダウンチャート作成"""
        # 図のサイズ設定
        fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)

        # データ準備と検証
        chart_data = self._prepare_burndown_chart_data(timeline)

        # ラインを描画
        self._plot_ideal_line(ax, chart_data["ideal_line"])
        self._plot_actual_line(ax, chart_data["actual_line"])

        # 現在日マーカー
        self._plot_today_marker(ax, timeline)

        # スタイル設定
        self._setup_chart_style(ax, timeline, "バーンダウンチャート")

        return fig

    def _prepare_burndown_chart_data(self, timeline: ProjectTimeline) -> dict:
        """バーンダウンチャート用データを準備"""
        ideal_line = self.calculator.calculate_ideal_line(timeline)
        actual_line = self.calculator.calculate_actual_line(timeline)

        if not ideal_line:
            raise ChartGeneratorError(
                f"No ideal line data available for project {timeline.project_id}. "
                "Check that the project has valid start/end dates and estimated hours."
            )
        if not actual_line:
            raise ChartGeneratorError(
                f"No actual data available for project {timeline.project_id}. "
                "Check that the project has daily snapshots with progress data."
            )

        return {
            "ideal_line": ideal_line,
            "actual_line": actual_line,
        }

    def _create_scope_chart(
        self, timeline: ProjectTimeline, show_changes: bool, width: int, height: int
    ) -> Figure:
        """スコープ変更チャート作成"""
        # 図のサイズ設定
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        # データ準備と検証
        scope_trend = self._prepare_scope_chart_data(timeline)

        # 総工数推移線を描画
        self._plot_scope_trend_line(ax, scope_trend)

        # スコープ変更マーカーを描画
        if show_changes:
            self._plot_scope_change_markers(ax, timeline)

        # スタイル設定
        self._setup_scope_chart_style(ax, timeline)

        return fig

    def _prepare_scope_chart_data(self, timeline: ProjectTimeline) -> list:
        """スコープチャート用データを準備"""
        scope_trend = self.calculator.calculate_scope_trend_line(timeline)

        if not scope_trend:
            raise ChartGeneratorError(
                f"No scope trend data available for project {timeline.project_id}. "
                "Check that the project has daily snapshots with total hours data."
            )

        return scope_trend

    def _plot_scope_trend_line(self, ax, scope_trend: list) -> None:
        """総工数推移線を描画"""
        scope_dates, scope_hours = zip(*scope_trend)
        scope_label = (
            "Total Hours Trend"
            if (hasattr(self, "_no_japanese_font") and self._no_japanese_font)
            else "総工数推移"
        )
        ax.plot(
            scope_dates,
            scope_hours,
            label=scope_label,
            color=self.config.chart.colors.scope,
            linestyle=self.config.chart.line_styles.scope,
            linewidth=3,
            marker="s",
            markersize=5,
        )

    def _plot_scope_change_markers(self, ax, timeline: ProjectTimeline) -> None:
        """スコープ変更マーカーを描画"""
        if not timeline.scope_changes:
            return

        increase_label_added = False
        decrease_label_added = False

        for change in timeline.scope_changes:
            change_date = change["date"]
            hours_delta = change["hours_delta"]

            # 変更日の総工数取得
            snapshot = timeline.get_snapshot_by_date(
                change_date
                if isinstance(change_date, date)
                else date.fromisoformat(change_date)
            )
            if not snapshot:
                continue

            total_hours = snapshot["total_estimated_hours"]

            # 増加・減少でマーカーを分ける
            if hours_delta > 0:
                label = "スコープ増加" if not increase_label_added else ""
                ax.scatter(
                    change_date,
                    total_hours,
                    color="red",
                    marker="^",
                    s=100,
                    label=label,
                    zorder=5,
                )
                increase_label_added = True
            else:
                label = "スコープ減少" if not decrease_label_added else ""
                ax.scatter(
                    change_date,
                    total_hours,
                    color="green",
                    marker="v",
                    s=100,
                    label=label,
                    zorder=5,
                )
                decrease_label_added = True

    def _setup_scope_chart_style(self, ax, timeline: ProjectTimeline) -> None:
        """スコープチャート固有のスタイル設定"""
        self._setup_chart_style(ax, timeline, "スコープ変更チャート")
        y_label = (
            "Total Hours"
            if (hasattr(self, "_no_japanese_font") and self._no_japanese_font)
            else "総工数 (時間)"
        )
        ax.set_ylabel(y_label)

    def _create_combined_chart(
        self, timeline: ProjectTimeline, width: int, height: int
    ) -> Figure:
        """統合チャート作成"""
        # 図のサイズ設定
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))

        # データ準備と検証
        chart_data = self._prepare_combined_chart_data(timeline)

        # 各ラインを描画
        self._plot_ideal_line(ax, chart_data["ideal_line"])
        self._plot_actual_line(ax, chart_data["actual_line"])
        if chart_data["dynamic_ideal_line"]:
            self._plot_dynamic_ideal_line(ax, chart_data["dynamic_ideal_line"])

        # 現在日マーカー
        self._plot_today_marker(ax, timeline)

        # スコープ変更エリア
        self._plot_scope_change_areas(ax, timeline)

        # スタイル設定
        self._setup_chart_style(ax, timeline, "統合バーンダウンチャート")

        return fig

    def _prepare_combined_chart_data(self, timeline: ProjectTimeline) -> dict:
        """統合チャート用データを準備"""
        ideal_line = self.calculator.calculate_ideal_line(timeline)
        actual_line = self.calculator.calculate_actual_line(timeline)
        dynamic_ideal_line = self.calculator.calculate_dynamic_ideal_line(timeline)

        if not ideal_line:
            raise ChartGeneratorError(
                f"No ideal line data available for project {timeline.project_id}. "
                "Check that the project has valid start/end dates and estimated hours."
            )
        if not actual_line:
            raise ChartGeneratorError(
                f"No actual data available for project {timeline.project_id}. "
                "Check that the project has daily snapshots with progress data."
            )

        return {
            "ideal_line": ideal_line,
            "actual_line": actual_line,
            "dynamic_ideal_line": dynamic_ideal_line,
        }

    def _plot_ideal_line(self, ax, ideal_line: list) -> None:
        """理想線を描画"""
        ideal_dates, ideal_hours = zip(*ideal_line)
        ideal_label = (
            "Ideal Line"
            if (hasattr(self, "_no_japanese_font") and self._no_japanese_font)
            else "理想線"
        )
        ax.plot(
            ideal_dates,
            ideal_hours,
            label=ideal_label,
            color=self.config.chart.colors.ideal,
            linestyle=self.config.chart.line_styles.ideal,
            linewidth=2,
        )

    def _plot_actual_line(self, ax, actual_line: list) -> None:
        """実際線を描画"""
        actual_dates, actual_hours = zip(*actual_line)
        actual_label = (
            "Actual Line"
            if (hasattr(self, "_no_japanese_font") and self._no_japanese_font)
            else "実際線"
        )
        ax.plot(
            actual_dates,
            actual_hours,
            label=actual_label,
            color=self.config.chart.colors.actual,
            linestyle=self.config.chart.line_styles.actual,
            linewidth=2,
            marker="o",
            markersize=4,
        )

    def _plot_dynamic_ideal_line(self, ax, dynamic_ideal_line: list) -> None:
        """動的理想線を描画"""
        dynamic_dates, dynamic_hours = zip(*dynamic_ideal_line)
        dynamic_label = (
            "Dynamic Ideal Line"
            if (hasattr(self, "_no_japanese_font") and self._no_japanese_font)
            else "動的理想線"
        )
        ax.plot(
            dynamic_dates,
            dynamic_hours,
            label=dynamic_label,
            color=self.config.chart.colors.dynamic_ideal,
            linestyle=self.config.chart.line_styles.dynamic_ideal,
            linewidth=2,
            alpha=0.8,
        )

    def _plot_today_marker(self, ax, timeline: ProjectTimeline) -> None:
        """現在日マーカーを描画"""
        today = date.today()
        if timeline.start_date <= today <= (timeline.end_date or today):
            today_label = (
                "Today"
                if (hasattr(self, "_no_japanese_font") and self._no_japanese_font)
                else "現在日"
            )
            ax.axvline(
                date2num(today),
                color="gray",
                linestyle="--",
                alpha=0.7,
                label=today_label,
            )

    def _plot_scope_change_areas(self, ax, timeline: ProjectTimeline) -> None:
        """スコープ変更影響エリアを描画"""
        if not timeline.scope_changes:
            return

        scope_label_added = False
        for change in timeline.scope_changes:
            if abs(change["hours_delta"]) >= 8.0:  # 中程度以上の変更のみ表示
                change_date = change["date"]
                if isinstance(change_date, str):
                    change_date = date.fromisoformat(change_date)

                change_date_num = date2num(change_date)
                label = "スコープ変更" if not scope_label_added else ""
                ax.axvspan(
                    change_date_num,
                    change_date_num,
                    alpha=0.2,
                    color="yellow",
                    label=label,
                )
                scope_label_added = True

    def _setup_chart_style(
        self, ax: Axes, timeline: ProjectTimeline, title: str
    ) -> None:
        """チャートスタイル設定"""
        # 日本語フォントがない場合の英語ラベル
        if hasattr(self, "_no_japanese_font") and self._no_japanese_font:
            title_map = {
                "バーンダウンチャート": "Burndown Chart",
                "スコープ変更チャート": "Scope Change Chart",
                "統合バーンダウンチャート": "Combined Burndown Chart",
            }
            english_title = title_map.get(title, title)
            # プロジェクト名も英語化（日本語文字を含む場合）
            project_name = timeline.project_name
            if any(ord(char) > 127 for char in project_name):
                project_name = f"Project {timeline.project_id}"
            ax.set_title(
                f"{project_name} - {english_title}",
                fontsize=12,  # タイトルフォントサイズを16から12に変更
                fontweight="bold",
                pad=20,
            )
            ax.set_xlabel("Date", fontsize=8)  # X軸ラベルフォントサイズを12から8に変更
            ax.set_ylabel(
                "Remaining Hours", fontsize=8
            )  # Y軸ラベルフォントサイズを12から8に変更
        else:
            ax.set_title(
                f"{timeline.project_name} - {title}",
                fontsize=12,  # タイトルフォントサイズを16から12に変更
                fontweight="bold",
                pad=20,
            )
            ax.set_xlabel("日付", fontsize=8)  # X軸ラベルフォントサイズを12から8に変更
            ax.set_ylabel(
                "残り工数 (時間)", fontsize=8
            )  # Y軸ラベルフォントサイズを12から8に変更

        # グリッド
        ax.grid(True, alpha=0.3, color=self.config.chart.colors.grid)

        # 軸フォーマット（日付フォーマットを%Y-%m-%dに変更）
        from matplotlib.dates import DayLocator

        ax.xaxis.set_major_locator(DayLocator(interval=2))  # 2日間隔で表示
        ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))  # yyyy-mm-dd形式に変更

        # 凡例（フォントサイズを小さく）
        ax.legend(
            loc="upper right", frameon=True, fancybox=True, shadow=True, fontsize=8
        )

        # 背景色
        ax.set_facecolor(self.config.chart.colors.background)

        # 軸の範囲調整
        if timeline.snapshots:
            y_max = max(
                snapshot["total_estimated_hours"] for snapshot in timeline.snapshots
            )
            ax.set_ylim(0, y_max * 1.1)

        # X軸の範囲
        start_num = date2num(timeline.start_date)
        end_num = date2num(timeline.end_date or date.today())
        ax.set_xlim(start_num, end_num)

        # 軸ラベルの回転（フォントサイズも小さく）
        plt.setp(
            ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=6
        )  # 目盛りフォントサイズを追加
        plt.setp(
            ax.yaxis.get_majorticklabels(), fontsize=6
        )  # Y軸目盛りフォントサイズを追加


def get_chart_generator() -> ChartGenerator:
    """
    チャート生成器の取得

    Returns:
        ChartGenerator: チャート生成器インスタンス

    Raises:
        ChartGeneratorError: チャート生成器作成に失敗した場合
    """
    try:
        return ChartGenerator()
    except Exception as e:
        raise ChartGeneratorError(f"Failed to create chart generator: {e}") from e
