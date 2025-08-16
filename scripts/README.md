# Scripts Directory

このディレクトリには、Redmine環境のセットアップとテストデータ作成に関するスクリプトが含まれています。

## 🚀 メインスクリプト

### `setup_complete_test_environment.sh`

**目的**: Redmineテスト環境の完全自動セットアップ
**説明**: このスクリプト1つでRedmineコンテナの起動からテストデータ作成まで全て自動実行
**使用方法**:

```bash
./scripts/setup_complete_test_environment.sh
```

**実行内容**:

1. Redmineコンテナの起動
2. 管理者ユーザーとAPIキーの設定
3. 基本マスターデータ（トラッカー、ステータス、優先度、ロール）の作成
4. テストプロジェクトの作成
5. バージョン（v1.0.0, v1.1.0, v2.0.0）の作成
6. 予定工数付きテストチケット9件の作成

**出力**: バーンダウンチャート開発用の完全なテストデータセット

## 🔧 サポートスクリプト

### `setup-admin.sh`

**目的**: Redmine管理者ユーザーとAPIキーの設定
**説明**: 管理者ユーザー（admin/admin）とAPIキー（固定値）を確実に設定
**使用方法**:

```bash
./scripts/setup-admin.sh
```

**特徴**:

- 固定APIキー: `048110ce3e4a78b218aede2826b01fbc90dff412`
- 開発用途に最適化された設定
- コンテナ再起動後も設定が保持される
- `setup_complete_test_environment.sh`から自動実行される

**注意**: 通常は`setup_complete_test_environment.sh`を実行すれば十分ですが、管理者設定のみを実行したい場合や、デバッグ時に個別実行できます。

### `create_test_issues.sh`

**目的**: テストチケットの作成
**説明**: 予定工数とバージョン紐づけ済みのテストチケット8件を作成
**使用方法**:

```bash
./scripts/create_test_issues.sh
```

**作成されるチケット**:

- v1.0.0向け: 3件（28時間）
- v1.1.0向け: 2件（18時間）
- v2.0.0向け: 3件（76時間）
- 合計: 8件、122時間

**注意**: 通常は`setup_complete_test_environment.sh`を実行すれば十分ですが、プロジェクトとバージョンが既に存在する状態でチケットのみを追加したい場合に使用します。

## 🔄 使用パターン

### 初回セットアップ

```bash
# 完全自動セットアップ（推奨）
./scripts/setup_complete_test_environment.sh
```

### 手動セットアップ

```bash
# 1. Redmine起動
docker compose up -d

# 2. 管理者設定
./scripts/setup-admin.sh

# 3. チケット作成（プロジェクト・バージョンは手動作成後）
./scripts/create_test_issues.sh
```

### 環境リセット

```bash
# コンテナ停止・削除
docker compose down -v

# 完全再セットアップ
./scripts/setup_complete_test_environment.sh
```

## 📊 作成されるテストデータ

| 項目 | 内容 |
|------|------|
| プロジェクト | テストプロジェクト (test-project) |
| バージョン | v1.0.0, v1.1.0, v2.0.0 |
| チケット数 | 9件（テスト用1件含む） |
| 総予定工数 | 130時間 |
| API接続 | <http://localhost:3000> |
| 認証情報 | admin/admin, APIキー固定 |

このテストデータはRedmineバーンダウンチャート開発に必要な全ての要素を含んでいます。
