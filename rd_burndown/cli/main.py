"""メインCLIエントリーポイント"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

from .. import __version__
from ..utils.config import get_config_manager
from .chart import add_chart_commands
from .data import add_data_commands
from .project import add_project_commands

# Rich traceback 有効化
install(show_locals=True)

console = Console()


@click.group()
@click.version_option(__version__, prog_name="rd-burndown")
@click.option(
    "--config", type=click.Path(exists=True, path_type=Path), help="設定ファイルのパス"
)
@click.option("--verbose", "-v", is_flag=True, help="詳細出力")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool) -> None:
    """Redmine バーンダウンチャート生成ツール

    Redmine v4系で管理されたチケットの工数に対するバーンダウンチャートを作成します。
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_manager"] = get_config_manager(config)


@cli.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """設定管理コマンド"""


@config.command()
@click.option("--interactive", "-i", is_flag=True, help="対話式設定")
@click.option("--force", "-f", is_flag=True, help="既存設定を上書き")
@click.pass_context
def init(ctx: click.Context, interactive: bool, force: bool) -> None:
    """初期設定ウィザード"""
    config_manager = ctx.obj["config_manager"]
    verbose = ctx.obj["verbose"]

    if config_manager.config_path.exists() and not force:
        console.print(
            f"[yellow]設定ファイルが既に存在します: {config_manager.config_path}[/yellow]"
        )
        console.print(
            "[yellow]--force オプションを使用して上書きしてください。[/yellow]"
        )
        return

    if interactive:
        console.print("[bold blue]rd-burndown 初期設定[/bold blue]")
        console.print()

        # Redmine URL 入力
        redmine_url = click.prompt(
            "Redmine URL", default="http://localhost:3000", type=str
        )

        # API キー入力
        api_key = click.prompt("Redmine API キー", type=str, hide_input=True)

        # 出力ディレクトリ入力
        output_dir = click.prompt("出力ディレクトリ", default="./output", type=str)

        # キャッシュディレクトリ入力
        cache_dir = click.prompt("キャッシュディレクトリ", default="./cache", type=str)

        # 設定作成
        config = config_manager.create_default_config()
        config.redmine.url = redmine_url
        config.redmine.api_key = api_key
        config.output.output_dir = output_dir
        config.data.cache_dir = cache_dir

        config_manager.save_config(config)

        console.print(
            f"[green]設定ファイルを作成しました: {config_manager.config_path}[/green]"
        )

        # 接続テスト
        console.print("\n[blue]接続テストを実行中...[/blue]")
        from ..core.redmine_client import RedmineClient

        try:
            client = RedmineClient(config)
            if client.test_connection():
                user = client.get_current_user()
                console.print(
                    f"[green]✓ 接続成功: {user.get('login', 'Unknown')}[/green]"
                )
            else:
                console.print("[red]✗ 接続失敗[/red]")
        except Exception as e:
            console.print(f"[red]✗ 接続エラー: {e}[/red]")
    else:
        # 非対話式：デフォルト設定作成
        config = config_manager.create_default_config()
        console.print(
            f"[green]デフォルト設定ファイルを作成しました: {config_manager.config_path}[/green]"
        )
        console.print("[yellow]設定を編集してください。[/yellow]")

    if verbose:
        console.print(f"\n[dim]設定ファイルパス: {config_manager.config_path}[/dim]")


@config.command()
@click.option(
    "--format", "output_format", type=click.Choice(["table", "json"]), default="table"
)
@click.option("--section", type=str, help="表示セクション")
@click.pass_context
def show(ctx: click.Context, output_format: str, section: Optional[str]) -> None:
    """現在設定表示"""
    config_manager = ctx.obj["config_manager"]
    config = config_manager.get_config()

    if output_format == "json":
        import json

        if section:
            section_data = getattr(config, section, None)
            if section_data:
                console.print(
                    json.dumps(section_data.model_dump(), indent=2, ensure_ascii=False)
                )
            else:
                console.print(f"[red]セクション '{section}' が見つかりません[/red]")
        else:
            console.print(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))
    else:
        from rich.table import Table

        table = Table(title="現在の設定")
        table.add_column("セクション", style="cyan")
        table.add_column("項目", style="magenta")
        table.add_column("値", style="green")

        config_dict = config.model_dump()

        for section_name, section_values in config_dict.items():
            if section and section_name != section:
                continue

            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            table.add_row(
                                section_name, f"{key}.{sub_key}", str(sub_value)
                            )
                    else:
                        # API キーは隠す
                        if key == "api_key" and value:
                            display_value = "*" * 8 + str(value)[-4:]
                        else:
                            display_value = str(value)
                        table.add_row(section_name, str(key), display_value)
            else:
                table.add_row(section_name, "", str(section_values))

        console.print(table)


# サブコマンドを追加（モジュールレベルで実行）
add_project_commands(cli)
add_chart_commands(cli)
add_data_commands(cli)


def main() -> None:
    """メイン関数"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]中断されました[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
