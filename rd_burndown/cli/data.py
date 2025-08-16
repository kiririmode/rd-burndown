"""データ管理コマンド"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from rd_burndown.core.data_manager import get_data_manager

console = Console()


@click.group()
@click.pass_context
def data(ctx: click.Context) -> None:
    """データ管理コマンド"""


@data.command()
@click.argument("project_id", type=int)
@click.option(
    "--incremental", is_flag=True, default=True, help="増分更新（デフォルト）"
)
@click.option("--full", is_flag=True, help="全データ更新")
@click.option(
    "--since", type=click.DateTime(formats=["%Y-%m-%d"]), help="指定日以降の変更のみ"
)
@click.pass_context
def fetch(
    ctx: click.Context,
    project_id: int,
    incremental: bool,
    full: bool,
    since: Optional[datetime],
) -> None:
    """日常的なデータ更新（増分取得）

    PROJECT_ID: 更新対象プロジェクトID
    """
    verbose = ctx.obj["verbose"]
    data_manager = get_data_manager()

    # フルアップデートが指定された場合は増分更新を無効化
    if full:
        incremental = False

    # 日付変換
    since_date = since.date() if since else None

    console.print(f"[blue]プロジェクト {project_id} のデータを更新中...[/blue]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("データ取得中...", total=None)

            data_manager.fetch_project_updates(
                project_id=project_id,
                incremental=incremental,
                since_date=since_date,
            )

            progress.update(task, description="完了")

        console.print(
            f"[green]✓ プロジェクト {project_id} のデータ更新が完了しました[/green]"
        )

        if verbose:
            # 更新後の状態を表示
            status = data_manager.get_cache_status(project_id)
            console.print("\n[dim]更新後の状態:[/dim]")
            console.print(f"  チケット数: {status['tickets_count']}")
            console.print(f"  スナップショット数: {status['snapshots_count']}")
            console.print(f"  スコープ変更数: {status['scope_changes_count']}")

    except Exception as e:
        console.print(f"[red]✗ データ更新に失敗しました: {e}[/red]")
        raise click.ClickException(f"Data fetch failed: {e}") from e


@data.command()
@click.argument("action", type=click.Choice(["clear", "status", "size"]))
@click.option(
    "--project-id", type=int, help="プロジェクトID（指定時は該当プロジェクトのみ）"
)
@click.pass_context
def cache(ctx: click.Context, action: str, project_id: Optional[int]) -> None:
    """キャッシュ管理

    ACTION: 実行アクション (clear|status|size)
    """
    verbose = ctx.obj["verbose"]
    data_manager = get_data_manager()

    if action == "clear":
        if project_id:
            console.print(
                f"[yellow]プロジェクト {project_id} のキャッシュをクリア中...[/yellow]"
            )
            try:
                data_manager.clear_project_cache(project_id)
                console.print(
                    f"[green]✓ プロジェクト {project_id} のキャッシュをクリアしました[/green]"
                )
            except Exception as e:
                console.print(f"[red]✗ キャッシュクリアに失敗しました: {e}[/red]")
                raise click.ClickException(f"Cache clear failed: {e}") from e
        else:
            console.print(
                "[red]プロジェクトIDを指定してください（全体クリアは未実装）[/red]"
            )

    elif action == "status":
        try:
            status = data_manager.get_cache_status(project_id)

            if project_id:
                # 特定プロジェクトの状態
                if "error" in status:
                    console.print(f"[red]{status['error']}[/red]")
                else:
                    table = Table(title=f"プロジェクト {project_id} キャッシュ状態")
                    table.add_column("項目", style="cyan")
                    table.add_column("値", style="green")

                    table.add_row("プロジェクト名", status["project_name"])
                    table.add_row("チケット数", str(status["tickets_count"]))
                    table.add_row("スナップショット数", str(status["snapshots_count"]))
                    table.add_row("スコープ変更数", str(status["scope_changes_count"]))
                    table.add_row("最終更新日時", str(status["last_update"] or "なし"))
                    table.add_row(
                        "データベースサイズ",
                        f"{status['database_size'] / 1024 / 1024:.2f} MB",
                    )

                    console.print(table)
            else:
                # 全体の状態
                db_info = status["database_info"]
                table = Table(title="キャッシュ全体状態")
                table.add_column("項目", style="cyan")
                table.add_column("値", style="green")

                table.add_row("データベースバージョン", str(db_info["version"]))
                table.add_row(
                    "データベースサイズ",
                    f"{db_info['file_size_bytes'] / 1024 / 1024:.2f} MB",
                )
                table.add_row("キャッシュディレクトリ", status["cache_directory"])
                table.add_row("TTL (時間)", str(status["cache_ttl_hours"]))

                if verbose:
                    table.add_row("プロジェクト数", str(db_info["tables"]["projects"]))
                    table.add_row("チケット数", str(db_info["tables"]["tickets"]))
                    table.add_row(
                        "スナップショット数", str(db_info["tables"]["daily_snapshots"])
                    )
                    table.add_row(
                        "スコープ変更数", str(db_info["tables"]["scope_changes"])
                    )

                console.print(table)

        except Exception as e:
            console.print(f"[red]✗ キャッシュ状態取得に失敗しました: {e}[/red]")
            raise click.ClickException(f"Cache status failed: {e}") from e

    elif action == "size":
        try:
            status = data_manager.get_cache_status(project_id)

            if project_id:
                if "error" in status:
                    console.print(f"[red]{status['error']}[/red]")
                else:
                    size_mb = status["database_size"] / 1024 / 1024
                    console.print(f"プロジェクト {project_id}: {size_mb:.2f} MB")
            else:
                db_info = status["database_info"]
                size_mb = db_info["file_size_bytes"] / 1024 / 1024
                console.print(f"データベース全体: {size_mb:.2f} MB")

        except Exception as e:
            console.print(f"[red]✗ キャッシュサイズ取得に失敗しました: {e}[/red]")
            raise click.ClickException(f"Cache size failed: {e}") from e


@data.command()
@click.argument("project_id", type=int)
@click.option(
    "--format", "output_format", type=click.Choice(["csv", "json"]), default="json"
)
@click.option("--output", type=click.Path(path_type=Path), help="出力ファイルパス")
@click.option(
    "--from", "from_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="開始日"
)
@click.option(
    "--to", "to_date", type=click.DateTime(formats=["%Y-%m-%d"]), help="終了日"
)
@click.pass_context
def export(
    ctx: click.Context,
    project_id: int,
    output_format: str,
    output: Optional[Path],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> None:
    """データエクスポート

    PROJECT_ID: エクスポート対象プロジェクトID
    """
    verbose = ctx.obj["verbose"]
    data_manager = get_data_manager()

    # 出力パス決定
    if output is None:
        output = Path(f"project_{project_id}_export.{output_format}")

    # 日付変換
    start_date = from_date.date() if from_date else None
    end_date = to_date.date() if to_date else None

    console.print(f"[blue]プロジェクト {project_id} のデータをエクスポート中...[/blue]")

    try:
        # プロジェクトタイムラインデータ取得
        timeline_data = data_manager.get_project_timeline(project_id)
        if not timeline_data:
            raise click.ClickException(f"Project {project_id} not found")

        # 日付フィルタリング
        snapshots = timeline_data["snapshots"]
        scope_changes = timeline_data["scope_changes"]

        if start_date or end_date:
            filtered_snapshots = []
            filtered_scope_changes = []

            for snapshot in snapshots:
                snapshot_date = snapshot["date"]
                if isinstance(snapshot_date, str):
                    snapshot_date = datetime.fromisoformat(snapshot_date).date()

                if start_date and snapshot_date < start_date:
                    continue
                if end_date and snapshot_date > end_date:
                    continue
                filtered_snapshots.append(snapshot)

            for change in scope_changes:
                change_date = change["date"]
                if isinstance(change_date, str):
                    change_date = datetime.fromisoformat(change_date).date()

                if start_date and change_date < start_date:
                    continue
                if end_date and change_date > end_date:
                    continue
                filtered_scope_changes.append(change)

            snapshots = filtered_snapshots
            scope_changes = filtered_scope_changes

        # エクスポート実行
        export_data = {
            "project": timeline_data["project"],
            "snapshots": snapshots,
            "scope_changes": scope_changes,
            "export_info": {
                "project_id": project_id,
                "format": output_format,
                "from_date": start_date.isoformat() if start_date else None,
                "to_date": end_date.isoformat() if end_date else None,
                "exported_at": datetime.now().isoformat(),
            },
        }

        if output_format == "json":
            with open(output, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        elif output_format == "csv":
            import csv

            # CSV出力（スナップショットのみ）
            with open(output, "w", newline="", encoding="utf-8") as f:
                if snapshots:
                    fieldnames = snapshots[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(snapshots)

        console.print(f"[green]✓ データを {output} にエクスポートしました[/green]")

        if verbose:
            console.print(f"  スナップショット数: {len(snapshots)}")
            console.print(f"  スコープ変更数: {len(scope_changes)}")
            console.print(f"  ファイルサイズ: {output.stat().st_size} bytes")

    except Exception as e:
        console.print(f"[red]✗ データエクスポートに失敗しました: {e}[/red]")
        raise click.ClickException(f"Data export failed: {e}") from e


# メインCLIにコマンドを追加
def add_data_commands(main_cli: click.Group) -> None:
    """メインCLIにdataコマンドを追加"""
    main_cli.add_command(data)
