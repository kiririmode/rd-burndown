"""SQLiteデータベース管理システム"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from rd_burndown.utils.helpers import ensure_directory

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """データベース関連エラー"""


class DatabaseManager:
    """SQLiteデータベース管理クラス"""

    CURRENT_VERSION = 2

    def __init__(self, db_path: Union[str, Path]):
        """
        初期化

        Args:
            db_path: データベースファイルパス
        """
        self.db_path = Path(db_path)
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """データベースディレクトリの確保"""
        if self.db_path.parent != Path("."):
            ensure_directory(self.db_path.parent)

    @contextmanager
    def get_connection(self, read_only: bool = False):
        """
        データベース接続のコンテキストマネージャー

        Args:
            read_only: 読み取り専用モード

        Yields:
            sqlite3.Connection: データベース接続
        """
        uri = f"file:{self.db_path}"
        if read_only:
            uri += "?mode=ro"

        conn = None
        try:
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}") from e
        finally:
            if conn:
                conn.close()

    def initialize_database(self) -> None:
        """データベースの初期化"""
        logger.info(f"Initializing database: {self.db_path}")

        with self.get_connection() as conn:
            # バージョン管理テーブル作成
            self._create_version_table(conn)

            # 現在のバージョンチェック
            current_version = self._get_current_version(conn)

            # マイグレーション実行
            if current_version < self.CURRENT_VERSION:
                self._run_migrations(conn, current_version)

            conn.commit()

        logger.info("Database initialization completed")

    def _create_version_table(self, conn: sqlite3.Connection) -> None:
        """バージョン管理テーブルの作成"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _get_current_version(self, conn: sqlite3.Connection) -> int:
        """現在のスキーマバージョンを取得"""
        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0

    def _run_migrations(self, conn: sqlite3.Connection, from_version: int) -> None:
        """マイグレーションの実行"""
        logger.info(
            f"Running migrations from version {from_version} to {self.CURRENT_VERSION}"
        )

        for version in range(from_version + 1, self.CURRENT_VERSION + 1):
            logger.info(f"Applying migration for version {version}")
            migration_method = getattr(self, f"_migrate_to_v{version}", None)

            if migration_method:
                migration_method(conn)
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (version,)
                )
            else:
                raise DatabaseError(f"Migration method for version {version} not found")

    def _migrate_to_v1(self, conn: sqlite3.Connection) -> None:
        """バージョン1へのマイグレーション - 初期スキーマ作成"""

        # プロジェクトテーブル
        conn.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                identifier TEXT UNIQUE,
                description TEXT,
                status INTEGER DEFAULT 1,
                start_date DATE,
                end_date DATE,
                created_on TIMESTAMP,
                updated_on TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # チケットテーブル
        conn.execute("""
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                subject TEXT NOT NULL,
                estimated_hours REAL,
                status_id INTEGER,
                status_name TEXT,
                created_on TIMESTAMP,
                updated_on TIMESTAMP,
                completed_on TIMESTAMP,
                assigned_to_id INTEGER,
                assigned_to_name TEXT,
                version_id INTEGER,
                version_name TEXT,
                custom_fields TEXT,  -- JSON形式で保存
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 日次スナップショットテーブル
        conn.execute("""
            CREATE TABLE daily_snapshots (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                total_estimated_hours REAL NOT NULL,
                completed_hours REAL NOT NULL,
                remaining_hours REAL NOT NULL,
                new_tickets_hours REAL DEFAULT 0,
                changed_hours REAL DEFAULT 0,
                deleted_hours REAL DEFAULT 0,
                active_ticket_count INTEGER NOT NULL,
                completed_ticket_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, project_id)
            )
        """)

        # スコープ変更テーブル
        conn.execute("""
            CREATE TABLE scope_changes (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                ticket_id INTEGER,
                ticket_subject TEXT,
                change_type TEXT NOT NULL,
                hours_delta REAL NOT NULL,
                old_hours REAL,
                new_hours REAL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # インデックス作成
        conn.execute("CREATE INDEX idx_tickets_project_id ON tickets(project_id)")
        conn.execute("CREATE INDEX idx_tickets_updated_on ON tickets(updated_on)")
        conn.execute(
            "CREATE INDEX idx_snapshots_project_date ON daily_snapshots(project_id, date)"
        )
        conn.execute(
            "CREATE INDEX idx_scope_changes_project_date ON scope_changes(project_id, date)"
        )

        logger.info("Initial schema (v1) created successfully")

    def _migrate_to_v2(self, conn: sqlite3.Connection) -> None:
        """バージョン2へのマイグレーション - ticket_journalsテーブル追加"""

        # チケット履歴テーブル
        conn.execute("""
            CREATE TABLE ticket_journals (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                ticket_id INTEGER NOT NULL,
                journal_id INTEGER NOT NULL,
                user_id INTEGER,
                user_name TEXT,
                created_on TIMESTAMP NOT NULL,
                notes TEXT,
                details TEXT,  -- JSON形式で変更詳細を保存
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, ticket_id, journal_id)
            )
        """)

        # インデックス作成
        conn.execute(
            "CREATE INDEX idx_ticket_journals_project_id ON ticket_journals(project_id)"
        )
        conn.execute(
            "CREATE INDEX idx_ticket_journals_ticket_id ON ticket_journals(ticket_id)"
        )
        conn.execute(
            "CREATE INDEX idx_ticket_journals_created_on ON ticket_journals(created_on)"
        )

        logger.info("ticket_journals table (v2) created successfully")

    def vacuum_database(self) -> None:
        """データベースの最適化"""
        logger.info("Vacuuming database")

        with self.get_connection() as conn:
            conn.execute("VACUUM")

        logger.info("Database vacuum completed")

    def get_database_info(self) -> dict[str, Any]:
        """データベース情報の取得"""
        with self.get_connection(read_only=True) as conn:
            # バージョン情報
            version = self._get_current_version(conn)

            # ファイルサイズ
            file_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            # テーブル統計
            tables_info = {}
            for table in [
                "projects",
                "tickets",
                "daily_snapshots",
                "scope_changes",
                "ticket_journals",
            ]:
                try:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")  # nosec B608
                    count = cursor.fetchone()[0]
                    tables_info[table] = count
                except sqlite3.Error:
                    tables_info[table] = 0

            return {
                "version": version,
                "file_path": str(self.db_path),
                "file_size_bytes": file_size,
                "tables": tables_info,
                "last_modified": datetime.fromtimestamp(self.db_path.stat().st_mtime)
                if self.db_path.exists()
                else None,
            }

    def backup_database(self, backup_path: Union[str, Path]) -> None:
        """データベースのバックアップ"""
        backup_path = Path(backup_path)
        ensure_directory(backup_path.parent)

        logger.info(f"Creating database backup: {backup_path}")

        with (
            self.get_connection(read_only=True) as source_conn,
            sqlite3.connect(backup_path) as backup_conn,
        ):
            source_conn.backup(backup_conn)

        logger.info("Database backup completed")

    def execute_query(
        self,
        query: str,
        params: Optional[tuple[Any, ...]] = None,
        fetch_one: bool = False,
        fetch_all: bool = True,
    ) -> Optional[Union[sqlite3.Row, list[sqlite3.Row]]]:
        """
        クエリの実行

        Args:
            query: SQL クエリ
            params: パラメータ
            fetch_one: 単一行取得
            fetch_all: 全行取得

        Returns:
            クエリ結果
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())

            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            conn.commit()
            return None

    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        """
        バッチ実行

        Args:
            query: SQL クエリ
            params_list: パラメータリスト
        """
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()


def get_database_manager(db_path: Optional[Union[str, Path]] = None) -> DatabaseManager:
    """
    データベースマネージャーの取得

    Args:
        db_path: データベースパス（Noneの場合はデフォルト）

    Returns:
        DatabaseManager: データベースマネージャー
    """
    if db_path is None:
        from rd_burndown.utils.config import get_config_manager

        config_manager = get_config_manager()
        config = config_manager.load_config()
        db_path = Path(config.data.cache_dir) / "rd_burndown.db"

    return DatabaseManager(db_path)
