# rd-burndown 設計ドキュメント

## 概要

rd-burndownは、Redmine v4系で管理されたチケットの工数に対するバーンダウンチャートを作成するサブコマンド式CLIツールです。標準的なバーンダウンチャートに加え、プロジェクト進行中のスコープ変更（総工数推移）も可視化できます。

## アーキテクチャ設計

### システム構成

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Core Engine    │    │ Chart Generator │
│                 │────│                 │────│                 │
│ - project       │    │ - models        │    │ - matplotlib    │
│ - chart         │    │ - redmine_client│    │ - seaborn       │
│ - data          │    │ - data_manager  │    │ - Japanese font │
│ - config        │    │ - calculator    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Configuration  │    │   Local Cache   │    │   Output Files  │
│                 │    │                 │    │                 │
│ - config.yaml   │    │ - SQLite DB     │    │ - PNG charts    │
│ - env variables │    │ - JSON cache    │    │ - CSV exports   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### パッケージ構造

```text
rd_burndown/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # メインCLIエントリーポイント
│   ├── project.py       # プロジェクト管理コマンド
│   ├── chart.py         # チャート生成コマンド
│   ├── data.py          # データ管理コマンド
│   └── config.py        # 設定管理コマンド
├── core/
│   ├── __init__.py
│   ├── models.py        # データモデル定義
│   ├── redmine_client.py # Redmine API クライアント
│   ├── data_manager.py  # データ管理・キャッシュ
│   ├── calculator.py    # バーンダウン計算エンジン
│   └── chart_generator.py # チャート生成エンジン
├── utils/
│   ├── __init__.py
│   ├── config.py        # 設定管理ユーティリティ
│   ├── date_utils.py    # 日付処理ユーティリティ
│   └── helpers.py       # 汎用ヘルパー関数
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_redmine_client.py
    ├── test_calculator.py
    └── test_chart_generator.py
```

## CLI仕様

### メインコマンド

```bash
rd-burndown [OPTIONS] COMMAND [ARGS]...
```

### サブコマンド体系

#### 1. project - プロジェクト管理

```bash
rd-burndown project COMMAND [OPTIONS]
```

**サブコマンド:**

- `list` - プロジェクト一覧表示

  ```bash
  rd-burndown project list [--format table|json]
  ```

- `info <project_id>` - プロジェクト詳細情報表示

  ```bash
  rd-burndown project info <project_id> [--verbose]
  ```

- `sync <project_id>` - プロジェクト全体の同期・初期化

  ```bash
  rd-burndown project sync <project_id>
    [--force]           # 強制完全同期
    [--include-closed]  # 終了チケットも含める
  ```

#### 2. chart - チャート生成

```bash
rd-burndown chart COMMAND [OPTIONS]
```

**サブコマンド:**

- `burndown <project_id>` - 標準バーンダウンチャート生成

  ```bash
  rd-burndown chart burndown <project_id>
    [--output PATH]
    [--from DATE]
    [--to DATE]
    [--width INT]
    [--height INT]
    [--dpi INT]
  ```

- `scope <project_id>` - スコープ変更チャート生成

  ```bash
  rd-burndown chart scope <project_id>
    [--output PATH]
    [--from DATE]
    [--to DATE]
    [--show-changes]
    [--width INT]
    [--height INT]
  ```

- `combined <project_id>` - 統合チャート生成

  ```bash
  rd-burndown chart combined <project_id>
    [--output PATH]
    [--from DATE]
    [--to DATE]
    [--width INT]
    [--height INT]
  ```

#### 3. data - データ管理

```bash
rd-burndown data COMMAND [OPTIONS]
```

**サブコマンド:**

- `fetch <project_id>` - 日常的なデータ更新（増分取得）

  ```bash
  rd-burndown data fetch <project_id>
    [--incremental]     # 増分更新（デフォルト）
    [--full]           # 全データ更新
    [--since DATE]     # 指定日以降の変更のみ
  ```

- `cache` - キャッシュ管理

  ```bash
  rd-burndown data cache [clear|status|size] [--project-id INT]
  ```

- `export <project_id>` - データエクスポート

  ```bash
  rd-burndown data export <project_id>
    [--format csv|json]
    [--output PATH]
    [--from DATE]
    [--to DATE]
  ```

#### 4. config - 設定管理

```bash
rd-burndown config COMMAND [OPTIONS]
```

**サブコマンド:**

- `init` - 初期設定ウィザード

  ```bash
  rd-burndown config init [--interactive] [--force]
  ```

- `show` - 現在設定表示

  ```bash
  rd-burndown config show [--format table|json] [--section SECTION]
  ```

## データ取得戦略: project sync vs data fetch

### project sync - プロジェクト管理レベル

**役割**: プロジェクト全体の同期・初期化

- 新規プロジェクトの登録
- プロジェクトメタデータの更新
- バージョン・マイルストーン情報の同期
- チケット一覧の初回取得
- **完全同期**（全データを最新状態に）

**使用タイミング**:

- 新しいプロジェクトを初めて追加する時
- プロジェクト設定が大幅に変更された時
- データ不整合が疑われる時

**動作例**:

```bash
rd-burndown project sync 1
```

```text
🔄 Syncing project "Website Renewal" (ID: 1)
├── 📋 Fetching project metadata... ✓
├── 🏷️  Syncing versions and milestones... ✓
├── 🎫 Fetching all tickets (0/245)... ✓
├── 📊 Building daily snapshots... ✓
├── 💾 Updating local database... ✓
└── ✅ Project sync completed (2.3 minutes)

Summary:
- 245 tickets processed
- 30 days of snapshots created
- Cache size: 2.1MB
```

### data fetch - データ更新レベル

**役割**: 日常的なデータ更新

- チケットの変更分のみ取得（増分更新）
- 新規チケットの追加
- ステータス変更履歴の更新
- **差分同期**（変更分のみ効率的に取得）

**使用タイミング**:

- 日次のデータ更新
- チャート生成前の最新化
- 定期実行スクリプトでの自動更新

**動作例**:

```bash
rd-burndown data fetch 1
```

```text
⚡ Fetching updates for project "Website Renewal" (ID: 1)
├── 🔍 Checking for changes since 2024-01-15 14:30... ✓
├── 🎫 Found 12 updated tickets... ✓
├── 📊 Updating snapshots for last 3 days... ✓
└── ✅ Data fetch completed (15 seconds)

Summary:
- 12 tickets updated
- 3 new daily snapshots
- Cache updated: +0.1MB
```

### 使い分け例

**初回セットアップ**:

```bash
# 新規プロジェクト追加
rd-burndown project sync 1

# チャート生成
rd-burndown chart burndown 1
```

**日常運用**:

```bash
# 朝の定期更新
rd-burndown data fetch 1

# 最新チャート生成
rd-burndown chart burndown 1
```

**トラブル時**:

```bash
# データ不整合が疑われる場合
rd-burndown data cache clear --project-id 1
rd-burndown project sync 1 --force
```

## データモデル設計

### 1. TicketData

```python
@dataclass
class TicketData:
    """チケットデータモデル"""
    id: int
    subject: str
    estimated_hours: Optional[float]
    created_on: datetime
    updated_on: datetime
    status_id: int
    status_name: str
    assigned_to_id: Optional[int]
    assigned_to_name: Optional[str]
    project_id: int
    version_id: Optional[int]
    version_name: Optional[str]
    custom_fields: Dict[str, Any]

    def is_completed(self) -> bool:
        """完了状態判定"""
        pass

    def completion_date(self) -> Optional[datetime]:
        """完了日取得"""
        pass
```

### 2. DailySnapshot

```python
@dataclass
class DailySnapshot:
    """日次工数スナップショット"""
    date: datetime.date
    project_id: int
    total_estimated_hours: float
    completed_hours: float
    remaining_hours: float
    new_tickets_hours: float
    changed_hours: float
    deleted_hours: float
    active_ticket_count: int
    completed_ticket_count: int

    def burn_rate(self) -> float:
        """バーンレート計算"""
        pass

    def scope_change(self) -> float:
        """スコープ変更量計算"""
        pass
```

### 3. ScopeChange

```python
@dataclass
class ScopeChange:
    """スコープ変更履歴"""
    date: datetime.date
    project_id: int
    change_type: str  # 'added', 'modified', 'removed'
    ticket_id: int
    ticket_subject: str
    hours_delta: float
    old_hours: Optional[float]
    new_hours: Optional[float]
    reason: str

    def impact_level(self) -> str:
        """影響度判定（high/medium/low）"""
        pass
```

### 4. ProjectTimeline

```python
@dataclass
class ProjectTimeline:
    """プロジェクト時系列データ"""
    project_id: int
    project_name: str
    start_date: datetime.date
    end_date: Optional[datetime.date]
    snapshots: List[DailySnapshot]
    scope_changes: List[ScopeChange]

    def ideal_line(self) -> List[Tuple[datetime.date, float]]:
        """理想線計算"""
        pass

    def actual_line(self) -> List[Tuple[datetime.date, float]]:
        """実際線計算"""
        pass

    def dynamic_ideal_line(self) -> List[Tuple[datetime.date, float]]:
        """動的理想線計算（スコープ変更考慮）"""
        pass

    def scope_trend_line(self) -> List[Tuple[datetime.date, float]]:
        """総工数推移線計算"""
        pass
```

### 5. RedmineProject

```python
@dataclass
class RedmineProject:
    """Redmineプロジェクトデータ"""
    id: int
    name: str
    identifier: str
    description: str
    status: int
    created_on: datetime
    updated_on: datetime
    versions: List[Dict[str, Any]]
    custom_fields: Dict[str, Any]

    def active_versions(self) -> List[Dict[str, Any]]:
        """アクティブバージョン取得"""
        pass
```

## チャート仕様

### 1. 標準バーンダウンチャート

**要素:**

- X軸: 日付（プロジェクト期間）
- Y軸: 残り工数（時間）
- 理想線: 開始日の総工数から終了日の0まで線形減少
- 実際線: 日次の実際残り工数をプロット
- 現在日マーカー: 縦線で現在日を表示

**視覚的特徴:**

- 理想線: 緑色（#2E8B57）、点線
- 実際線: 赤色（#DC143C）、実線、マーカー付き
- グリッド: 薄いグレー、細線
- 背景: 白色
- フォント: 日本語対応フォント（DejaVu Sans）

### 2. スコープ変更チャート

**要素:**

- X軸: 日付
- Y軸: 総工数（時間）
- 総工数推移線: 日次の総工数をプロット
- スコープ変更マーカー: 変更発生日に特別マーカー
- 変更量注釈: 大きな変更には数値注釈

**視覚的特徴:**

- 総工数線: 青色（#4169E1）、実線、太め
- 増加マーカー: 上向き三角、赤色
- 減少マーカー: 下向き三角、緑色
- 注釈: 背景色付きテキストボックス

### 3. 統合チャート

**要素:**

- 標準バーンダウンの全要素
- 動的理想線: スコープ変更を反映した理想線
- スコープ変更エリア: 変更による影響範囲をハイライト

**視覚的特徴:**

- 動的理想線: オレンジ色（#FF8C00）、破線
- 影響エリア: 薄い黄色の背景色
- 凡例: 右上に配置、全線種を説明

### チャート共通仕様

**サイズ・解像度:**

- デフォルト: 1200x800px
- DPI: 300（高品質印刷対応）
- フォーマット: PNG（透明背景オプション）

**日本語対応:**

- フォント: システムにインストール済みの日本語フォント自動選択
- エンコーディング: UTF-8
- タイトル・ラベル: 完全日本語対応

**アクセシビリティ:**

- カラーブラインド対応色選択
- 十分なコントラスト比
- 線種による区別（色だけに依存しない）

## 技術仕様

### 使用ライブラリ

**CLI Framework:**

- `click`: サブコマンド構造、オプション解析
- `rich`: 美しいターミナル出力、プログレスバー

**データ処理:**

- `requests`: HTTP API クライアント
- `pandas`: データ分析・操作
- `sqlite3`: ローカルデータベース
- `pydantic`: データバリデーション

**チャート生成:**

- `matplotlib`: 基本グラフ描画
- `seaborn`: 統計グラフ・美しいデザイン
- `japanize-matplotlib`: 日本語フォント対応

**設定管理:**

- `pyyaml`: YAML設定ファイル
- `python-dotenv`: 環境変数管理

**日付処理:**

- `pendulum`: タイムゾーン対応日付処理
- `holidays`: 祝日判定

### データベーススキーマ（SQLite）

```sql
-- プロジェクトテーブル
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    identifier TEXT UNIQUE,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- チケットテーブル
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
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
    version_name TEXT
);

-- 日次スナップショットテーブル
CREATE TABLE daily_snapshots (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    project_id INTEGER REFERENCES projects(id),
    total_estimated_hours REAL NOT NULL,
    completed_hours REAL NOT NULL,
    remaining_hours REAL NOT NULL,
    new_tickets_hours REAL DEFAULT 0,
    changed_hours REAL DEFAULT 0,
    deleted_hours REAL DEFAULT 0,
    active_ticket_count INTEGER NOT NULL,
    completed_ticket_count INTEGER NOT NULL,
    UNIQUE(date, project_id)
);

-- スコープ変更テーブル
CREATE TABLE scope_changes (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    project_id INTEGER REFERENCES projects(id),
    ticket_id INTEGER,
    change_type TEXT NOT NULL,
    hours_delta REAL NOT NULL,
    old_hours REAL,
    new_hours REAL,
    reason TEXT
);

-- インデックス
CREATE INDEX idx_tickets_project_id ON tickets(project_id);
CREATE INDEX idx_snapshots_project_date ON daily_snapshots(project_id, date);
CREATE INDEX idx_scope_changes_project_date ON scope_changes(project_id, date);
```

### パフォーマンス要件

**API呼び出し最適化:**

- バッチ取得: 一度に100チケットまで取得
- レート制限: 1秒あたり最大5リクエスト
- リトライ機能: 指数バックオフ付き最大3回

**キャッシュ戦略:**

- 増分更新: 最終更新日以降のデータのみ取得
- TTL設定: プロジェクトメタデータ1時間、チケットデータ15分
- 圧縮: JSON データの gzip 圧縮保存

**メモリ管理:**

- 大量データのチャンク処理
- 使用メモリ上限: 512MB
- ガベージコレクション最適化

### エラーハンドリング戦略

**API エラー:**

- 認証エラー: 明確なメッセージと設定ガイド
- ネットワークエラー: 自動リトライと手動再試行案内
- データ不整合: 警告表示と部分データでの継続

**データ検証:**

- 必須フィールドチェック
- 日付範囲検証
- 工数値の妥当性チェック

**ユーザーエラー:**

- コマンド引数検証
- ファイルパス存在チェック
- 設定値フォーマット検証

## 設定管理仕様

### config.yaml 構造

```yaml
# Redmine接続設定
redmine:
  url: "http://localhost:3000"
  api_key: "your-api-key-here"  # pragma: allowlist secret
  timeout: 30
  verify_ssl: true

# 出力設定
output:
  default_format: "png"
  default_width: 1200
  default_height: 800
  default_dpi: 300
  output_dir: "./output"

# チャート設定
chart:
  font_family: "DejaVu Sans"
  font_size: 12
  colors:
    ideal: "#2E8B57"
    actual: "#DC143C"
    scope: "#4169E1"
    dynamic_ideal: "#FF8C00"
    background: "#FFFFFF"
    grid: "#E0E0E0"
  line_styles:
    ideal: "dashed"
    actual: "solid"
    scope: "solid"
    dynamic_ideal: "dashdot"

# データ設定
data:
  cache_dir: "./cache"
  cache_ttl_hours: 1
  incremental_sync: true
  max_batch_size: 100

# 日付設定
date:
  timezone: "Asia/Tokyo"
  business_days_only: false
  exclude_holidays: true
  holiday_country: "JP"

# ログ設定
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/rd-burndown.log"
```

### 環境変数オーバーライド

```bash
# Redmine設定
export RD_REDMINE_URL="http://localhost:3000"
export RD_REDMINE_API_KEY="your-api-key"  # pragma: allowlist secret

# 出力設定
export RD_OUTPUT_DIR="./charts"
export RD_OUTPUT_FORMAT="png"

# キャッシュ設定
export RD_CACHE_DIR="./cache"
export RD_CACHE_TTL_HOURS="2"
```

## 実装ガイドライン

### 開発順序

#### Phase 1: 基盤実装

1. プロジェクト構造セットアップ
2. 設定管理システム実装
3. データモデル定義
4. Redmine API クライアント実装

#### Phase 2: コア機能実装

1. データ管理・キャッシュシステム
2. バーンダウン計算エンジン
3. 基本チャート生成機能
4. CLI基本構造（config, dataサブコマンド）

#### Phase 3: 高度な機能実装

1. スコープ変更追跡機能
2. 高度なチャート機能（scope, combinedチャート）
3. データエクスポート機能
4. CLI全サブコマンド完成

#### Phase 4: 品質向上

1. 包括的テストスイート
2. パフォーマンス最適化
3. エラーハンドリング強化
4. ドキュメント整備

### テスト戦略

**単体テスト:**

- すべてのコアモジュールに対してpytestベースのテスト
- モックを使用したAPI呼び出しテスト
- エッジケースとエラー条件のテスト

**統合テスト:**

- Redmine APIとの実際の連携テスト
- ファイル入出力テスト
- CLIコマンドの統合テスト

### 品質保証

**コード品質:**

- ruff: コードフォーマットとリント
- pyright: 型チェック
- pre-commit: 自動品質チェック

**カバレッジ:**

- 目標: 90%以上のコードカバレッジ
- pytest-cov による測定
- 重要な関数は100%カバレッジ

**CI/CD要件:**

- GitHub Actions による自動テスト
- 複数Pythonバージョン対応（3.9+）
- 自動リリース生成

## 拡張可能性

### 将来の機能拡張

**チャート種類:**

- ベロシティチャート
- 累積フローダイアグラム
- サイクルタイム分析

**出力形式:**

- SVG ベクター形式
- PDF レポート生成
- HTML インタラクティブチャート

**データソース:**

- Jira 連携
- GitHub Issues 連携
- CSV ファイル取り込み

**分析機能:**

- 予測アルゴリズム
- 統計分析レポート
- パフォーマンス指標計算

### アーキテクチャ拡張

**プラグインシステム:**

- カスタムデータソースプラグイン
- チャート描画プラグイン
- 分析アルゴリズムプラグイン

**API サーバー:**

- REST API サーバー機能
- Web UI フロントエンド
- リアルタイムダッシュボード

**分散処理:**

- 複数プロジェクト並列処理
- クラウドストレージ連携
- スケーラブルアーキテクチャ
