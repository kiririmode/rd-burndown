"""チャート生成コマンド"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from rd_burndown.core.chart_generator import get_chart_generator

console = Console()


@click.group()
@click.pass_context
def chart(ctx: click.Context) -> None:
    """チャート生成コマンド"""


@chart.command()
@click.argument("project_id", type=int)
@click.option("--output", type=click.Path(path_type=Path), help="出力パス")
@click.option(
    "--from", "from_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="開始日"
)
@click.option(
    "--to", "to_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="終了日"
)
@click.option(
    "--ideal-start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="理想線開始日（指定した日の残工数から理想線を開始）",
)
@click.option("--width", type=int, default=1200, help="幅")
@click.option("--height", type=int, default=800, help="高さ")
@click.option("--dpi", type=int, default=300, help="DPI")
@click.pass_context
def burndown(
    ctx: click.Context,
    project_id: int,
    output: Optional[Path],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    ideal_start_date: Optional[datetime],
    width: int,
    height: int,
    dpi: int,
) -> None:
    """標準バーンダウンチャート生成

    PROJECT_ID: 対象プロジェクトID
    """
    verbose = ctx.obj["verbose"]
    chart_generator = get_chart_generator()

    # 日付変換
    start_date = from_date.date() if from_date else None
    end_date = to_date.date() if to_date else None
    ideal_start = ideal_start_date.date() if ideal_start_date else None

    console.print(
        f"[blue]プロジェクト {project_id} のバーンダウンチャートを生成中...[/blue]"
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("チャート生成中...", total=None)

            output_path = chart_generator.generate_burndown_chart(
                project_id=project_id,
                output_path=output,
                start_date=start_date,
                end_date=end_date,
                ideal_start_date=ideal_start,
                width=width,
                height=height,
                dpi=dpi,
            )

            progress.update(task, description="生成完了")

        console.print(
            f"[green]✓ バーンダウンチャートを生成しました: {output_path}[/green]"
        )

        if verbose:
            file_size = output_path.stat().st_size
            console.print(f"  ファイルサイズ: {file_size / 1024:.1f} KB")
            console.print(f"  解像度: {width}x{height} ({dpi} DPI)")

    except Exception as e:
        console.print(f"[red]✗ バーンダウンチャート生成に失敗しました: {e}[/red]")
        raise click.ClickException(f"Burndown chart generation failed: {e}") from e


@chart.command()
@click.argument("project_id", type=int)
@click.option("--output", type=click.Path(path_type=Path), help="出力パス")
@click.option(
    "--from", "from_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="開始日"
)
@click.option(
    "--to", "to_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="終了日"
)
@click.option("--show-changes", is_flag=True, help="変更マーカー表示")
@click.option("--width", type=int, default=1200, help="幅")
@click.option("--height", type=int, default=800, help="高さ")
@click.pass_context
def scope(
    ctx: click.Context,
    project_id: int,
    output: Optional[Path],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    show_changes: bool,
    width: int,
    height: int,
) -> None:
    """スコープ変更チャート生成

    PROJECT_ID: 対象プロジェクトID
    """
    verbose = ctx.obj["verbose"]
    chart_generator = get_chart_generator()

    # 日付変換
    start_date = from_date.date() if from_date else None
    end_date = to_date.date() if to_date else None

    console.print(
        f"[blue]プロジェクト {project_id} のスコープ変更チャートを生成中...[/blue]"
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("チャート生成中...", total=None)

            output_path = chart_generator.generate_scope_chart(
                project_id=project_id,
                output_path=output,
                start_date=start_date,
                end_date=end_date,
                show_changes=show_changes,
                width=width,
                height=height,
            )

            progress.update(task, description="生成完了")

        console.print(
            f"[green]✓ スコープ変更チャートを生成しました: {output_path}[/green]"
        )

        if verbose:
            file_size = output_path.stat().st_size
            console.print(f"  ファイルサイズ: {file_size / 1024:.1f} KB")
            console.print(f"  解像度: {width}x{height}")

    except Exception as e:
        console.print(f"[red]✗ スコープ変更チャート生成に失敗しました: {e}[/red]")
        raise click.ClickException(f"Scope chart generation failed: {e}") from e


@chart.command()
@click.argument("project_id", type=int)
@click.option("--output", type=click.Path(path_type=Path), help="出力パス")
@click.option(
    "--from", "from_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="開始日"
)
@click.option(
    "--to", "to_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="終了日"
)
@click.option("--width", type=int, default=1200, help="幅")
@click.option("--height", type=int, default=800, help="高さ")
@click.pass_context
def combined(
    ctx: click.Context,
    project_id: int,
    output: Optional[Path],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    width: int,
    height: int,
) -> None:
    """統合チャート生成

    PROJECT_ID: 対象プロジェクトID
    """
    verbose = ctx.obj["verbose"]
    chart_generator = get_chart_generator()

    # 日付変換
    start_date = from_date.date() if from_date else None
    end_date = to_date.date() if to_date else None

    console.print(f"[blue]プロジェクト {project_id} の統合チャートを生成中...[/blue]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("チャート生成中...", total=None)

            output_path = chart_generator.generate_combined_chart(
                project_id=project_id,
                output_path=output,
                start_date=start_date,
                end_date=end_date,
                width=width,
                height=height,
            )

            progress.update(task, description="生成完了")

        console.print(f"[green]✓ 統合チャートを生成しました: {output_path}[/green]")

        if verbose:
            file_size = output_path.stat().st_size
            console.print(f"  ファイルサイズ: {file_size / 1024:.1f} KB")
            console.print(f"  解像度: {width}x{height}")

    except Exception as e:
        console.print(f"[red]✗ 統合チャート生成に失敗しました: {e}[/red]")
        raise click.ClickException(f"Combined chart generation failed: {e}") from e


# メインCLIにコマンドを追加
def add_chart_commands(main_cli: click.Group) -> None:
    """メインCLIにchartコマンドを追加"""
    main_cli.add_command(chart)
