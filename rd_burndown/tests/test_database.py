"""データベース管理システムのテスト"""

import sqlite3

import pytest

from rd_burndown.core.database import DatabaseError, DatabaseManager


class TestDatabaseManager:
    """データベースマネージャーのテスト"""

    def test_initialize_database(self, temp_dir):
        """データベース初期化のテスト"""
        db_path = temp_dir / "test.db"
        manager = DatabaseManager(db_path)

        # 初期化実行
        manager.initialize_database()

        # データベースファイルが作成されることを確認
        assert db_path.exists()

        # テーブルが作成されることを確認
        with manager.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

        expected_tables = {
            "schema_version",
            "projects",
            "tickets",
            "daily_snapshots",
            "scope_changes",
        }
        assert expected_tables.issubset(set(tables))

    def test_get_database_info(self, temp_dir):
        """データベース情報取得のテスト"""
        db_path = temp_dir / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize_database()

        info = manager.get_database_info()

        assert info["version"] == 1
        assert info["file_path"] == str(db_path)
        assert info["file_size_bytes"] > 0
        assert "projects" in info["tables"]
        assert "tickets" in info["tables"]
        assert info["last_modified"] is not None

    def test_backup_database(self, temp_dir):
        """データベースバックアップのテスト"""
        db_path = temp_dir / "test.db"
        backup_path = temp_dir / "backup.db"

        manager = DatabaseManager(db_path)
        manager.initialize_database()

        # バックアップ実行
        manager.backup_database(backup_path)

        # バックアップファイルが作成されることを確認
        assert backup_path.exists()

        # バックアップファイルが有効なSQLiteデータベースであることを確認
        with sqlite3.connect(backup_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

        assert "projects" in tables
        assert "tickets" in tables

    def test_execute_query(self, temp_dir):
        """クエリ実行のテスト"""
        db_path = temp_dir / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize_database()

        # データ挿入
        manager.execute_query(
            """INSERT INTO projects (id, name, identifier)
               VALUES (?, ?, ?)""",
            (1, "Test Project", "test"),
            fetch_all=False,
        )

        # データ取得（単一行）
        result = manager.execute_query(
            "SELECT name FROM projects WHERE id = ?",
            (1,),
            fetch_one=True,
        )
        assert result is not None
        assert result[0] == "Test Project"  # name is the only column in the SELECT

        # データ取得（全行）
        results = manager.execute_query(
            "SELECT * FROM projects",
            fetch_all=True,
        )
        assert results is not None
        assert len(results) == 1

    def test_execute_many(self, temp_dir):
        """バッチ実行のテスト"""
        db_path = temp_dir / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize_database()

        # バッチデータ挿入
        data = [
            (1, "Project 1", "proj1"),
            (2, "Project 2", "proj2"),
            (3, "Project 3", "proj3"),
        ]
        manager.execute_many(
            "INSERT INTO projects (id, name, identifier) VALUES (?, ?, ?)",
            data,
        )

        # 挿入されたデータの確認
        results = manager.execute_query("SELECT COUNT(*) FROM projects", fetch_one=True)
        assert results[0] == 3

    def test_vacuum_database(self, temp_dir):
        """データベース最適化のテスト"""
        db_path = temp_dir / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize_database()

        # バキューム実行（エラーが発生しないことを確認）
        manager.vacuum_database()

    def test_database_error_on_connection_failure(self, temp_dir):
        """接続失敗時のエラーハンドリングのテスト"""
        # 読み取り専用のディレクトリ内のパスでテスト
        db_path = temp_dir / "readonly" / "database.db"

        # 読み取り専用のディレクトリを作成
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # 読み取り専用

        try:
            manager = DatabaseManager(db_path)
            # 接続エラーが適切に処理されることを確認
            with pytest.raises(DatabaseError):
                manager.initialize_database()
        finally:
            # 後片付け
            readonly_dir.chmod(0o755)

    def test_migration_error_handling(self, temp_dir):
        """マイグレーションエラーハンドリングのテスト"""
        db_path = temp_dir / "test.db"

        # 無効なバージョンを設定したマネージャーを作成
        class BrokenDatabaseManager(DatabaseManager):
            CURRENT_VERSION = 999  # 存在しないバージョン

        manager = BrokenDatabaseManager(db_path)

        # マイグレーションエラーが発生することを確認
        with pytest.raises(DatabaseError, match="Migration method for version"):
            manager.initialize_database()


def test_get_database_manager_with_default_path():
    """デフォルトパスでのデータベースマネージャー取得のテスト"""
    from rd_burndown.core.database import get_database_manager

    # デフォルトパスでマネージャーを取得
    manager = get_database_manager()
    assert isinstance(manager, DatabaseManager)


def test_get_database_manager_with_custom_path(temp_dir):
    """カスタムパスでのデータベースマネージャー取得のテスト"""
    from rd_burndown.core.database import get_database_manager

    custom_path = temp_dir / "custom.db"
    manager = get_database_manager(custom_path)
    assert isinstance(manager, DatabaseManager)
    assert manager.db_path == custom_path
