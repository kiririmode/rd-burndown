#!/usr/bin/env python3
"""
Redmine接続テストスクリプト
"""

import sys

sys.path.insert(0, "/workspaces/rd-burndown")

from rd_burndown.core.redmine_client import RedmineClient
from rd_burndown.utils.config import get_config_manager


def test_connection():
    """接続テスト"""
    try:
        print("設定読み込み中...")
        config_manager = get_config_manager()
        config = config_manager.load_config()

        print(f"接続先: {config.redmine.url}")
        print(f"APIキー: {config.redmine.api_key[:8]}...")

        print("Redmineクライアント作成中...")
        client = RedmineClient(config)

        print("接続テスト実行中...")
        if client.test_connection():
            print("✓ 接続成功")

            print("現在のユーザー情報取得中...")
            user = client.get_current_user()
            print(f"ユーザー: {user.get('login', 'Unknown')}")

            print("プロジェクト一覧取得中...")
            projects = client.get_projects()
            print(f"プロジェクト数: {len(projects)}")

            for project in projects:
                print(f"- {project['name']} (ID: {project['id']})")

        else:
            print("✗ 接続失敗")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_connection()
