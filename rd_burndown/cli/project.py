"""プロジェクト管理コマンド"""

from __future__ import annotations

import json
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from rd_burndown.core.data_manager import get_data_manager
from rd_burndown.core.redmine_client import get_redmine_client

console = Console()


@click.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """プロジェクト管理コマンド"""


@project.command()
@click.option(
    "--format", "output_format", type=click.Choice(["table", "json"]), default="table"
)
@click.pass_context
def list(ctx: click.Context, output_format: str) -> None:
    """プロジェクト一覧表示"""
    verbose = ctx.obj["verbose"]
    redmine_client = get_redmine_client()

    console.print("[blue]プロジェクト一覧を取得中...[/blue]")

    try:
        projects = redmine_client.get_projects(include_closed=False)

        if output_format == "json":
            console.print(
                json.dumps(projects, ensure_ascii=False, indent=2, default=str)
            )
        else:
            table = Table(title="プロジェクト一覧")
            table.add_column("ID", style="cyan")
            table.add_column("名前", style="green")
            table.add_column("識別子", style="magenta")
            table.add_column("ステータス", style="yellow")

            for project_data in projects:
                status = (
                    "アクティブ" if project_data.get("status") == 1 else "非アクティブ"
                )
                table.add_row(
                    str(project_data["id"]),
                    project_data["name"],
                    project_data["identifier"],
                    status,
                )

            console.print(table)

        if verbose:
            console.print(f"\n[dim]総プロジェクト数: {len(projects)}[/dim]")

    except Exception as e:
        console.print(f"[red]✗ プロジェクト一覧取得に失敗しました: {e}[/red]")
        raise click.ClickException(f"Project list failed: {e}") from e


@project.command()
@click.argument("project_id", type=int)
@click.option("--verbose", "-v", is_flag=True, help="詳細情報表示")
@click.pass_context
def info(ctx: click.Context, project_id: int, verbose: bool) -> None:
    """プロジェクト詳細情報表示

    PROJECT_ID: 表示対象プロジェクトID
    """
    redmine_client = get_redmine_client()
    data_manager = get_data_manager()

    console.print(f"[blue]プロジェクト {project_id} の情報を取得中...[/blue]")

    try:
        # プロジェクト基本情報取得と表示
        project_data = redmine_client.get_project_data(project_id)
        _display_project_basic_info(project_data)

        # バージョン情報表示（詳細モード時）
        if verbose and project_data.versions:
            _display_project_versions(project_data.versions)

        # キャッシュ状態表示
        _display_cache_status(data_manager, project_id)

    except Exception as e:
        console.print(f"[red]✗ プロジェクト情報取得に失敗しました: {e}[/red]")
        raise click.ClickException(f"Project info failed: {e}") from e


def _display_project_basic_info(project_data) -> None:
    """プロジェクト基本情報を表示"""
    table = Table(title=f"プロジェクト情報: {project_data.name}")
    table.add_column("項目", style="cyan")
    table.add_column("値", style="green")

    table.add_row("ID", str(project_data.id))
    table.add_row("名前", project_data.name)
    table.add_row("識別子", project_data.identifier)
    table.add_row("説明", project_data.description or "なし")
    table.add_row(
        "ステータス", "アクティブ" if project_data.status == 1 else "非アクティブ"
    )
    table.add_row("作成日", project_data.created_on.strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("更新日", project_data.updated_on.strftime("%Y-%m-%d %H:%M:%S"))

    if project_data.start_date:
        table.add_row("開始日", project_data.start_date.strftime("%Y-%m-%d"))
    if project_data.end_date:
        table.add_row("終了日", project_data.end_date.strftime("%Y-%m-%d"))

    console.print(table)


def _display_project_versions(versions: list[dict[str, Any]]) -> None:
    """プロジェクトバージョン情報を表示"""
    version_table = Table(title="バージョン一覧")
    version_table.add_column("ID", style="cyan")
    version_table.add_column("名前", style="green")
    version_table.add_column("ステータス", style="yellow")

    for version in versions:
        version_table.add_row(
            str(version["id"]),
            version["name"],
            version.get("status", "unknown"),
        )

    console.print(version_table)


def _display_cache_status(data_manager, project_id: int) -> None:
    """キャッシュ状態を表示"""
    try:
        cache_status = data_manager.get_cache_status(project_id)
        if "error" not in cache_status:
            console.print("\n[dim]キャッシュ状態:[/dim]")
            console.print(f"  チケット数: {cache_status['tickets_count']}")
            console.print(f"  スナップショット数: {cache_status['snapshots_count']}")
            console.print(f"  最終更新: {cache_status['last_update'] or 'なし'}")
    except Exception:
        console.print("\n[dim]キャッシュ状態: 未同期[/dim]")


@project.command()
@click.argument("project_id", type=int)
@click.option("--force", "-f", is_flag=True, help="強制完全同期")
@click.option("--include-closed", is_flag=True, help="終了チケットも含める")
@click.pass_context
def sync(
    ctx: click.Context, project_id: int, force: bool, include_closed: bool
) -> None:
    """プロジェクト全体の同期・初期化

    PROJECT_ID: 同期対象プロジェクトID
    """
    verbose = ctx.obj["verbose"]
    data_manager = get_data_manager()

    console.print(f"[blue]プロジェクト {project_id} を同期中...[/blue]")

    if force:
        console.print("[yellow]強制完全同期を実行します[/yellow]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("プロジェクト同期中...", total=None)

            data_manager.sync_project(
                project_id=project_id,
                force=force,
                include_closed=include_closed,
            )

            progress.update(task, description="同期完了")

        console.print(
            f"[green]✓ プロジェクト {project_id} の同期が完了しました[/green]"
        )

        if verbose:
            # 同期後の状態を表示
            status = data_manager.get_cache_status(project_id)
            if "error" not in status:
                console.print("\n[dim]同期後の状態:[/dim]")
                console.print(f"  プロジェクト名: {status['project_name']}")
                console.print(f"  チケット数: {status['tickets_count']}")
                console.print(f"  スナップショット数: {status['snapshots_count']}")
                console.print(f"  スコープ変更数: {status['scope_changes_count']}")

    except Exception as e:
        console.print(f"[red]✗ プロジェクト同期に失敗しました: {e}[/red]")
        raise click.ClickException(f"Project sync failed: {e}") from e


# メインCLIにコマンドを追加
def add_project_commands(main_cli: click.Group) -> None:
    """メインCLIにprojectコマンドを追加"""
    main_cli.add_command(project)
