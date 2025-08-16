# 開発ガイドライン

このドキュメントには、このコードベースで作業する際の重要な情報が含まれています。これらのガイドラインに正確に従ってください。

## プロジェクト概要

本プロジェクトは、Redmine v4系で管理されたチケットの工数に対するバーンダウンチャートを作成するツールです。

## Redmine環境

### 起動方法
```bash
# コンテナ起動
docker compose up -d

# 管理者ユーザー・APIキーの自動設定（初回のみ推奨）
./scripts/setup-admin.sh
```

### 動作確認方法
1. コンテナ状態確認:
   ```bash
   docker ps
   ```
   
2. バージョン確認:
   ```bash
   docker exec redmine cat /usr/src/redmine/lib/redmine/version.rb
   ```
   
3. Web UI確認:
   - アクセス: http://localhost:3000
   - ログ確認: `docker logs redmine`

### 停止方法
```bash
docker compose down
```

### 構成
- Redmine 4.2.10 (ポート: 3000)
- PostgreSQL 15 (内部ポート: 5432)

### 認証情報
**管理者ユーザー（固定）:**
- ログイン: `admin`
- パスワード: `admin`
- APIキー: `048110ce3e4a78b218aede2826b01fbc90dff412`

**特徴:**
- データはボリュームに永続化されるため、コンテナ再起動後も認証情報は保持される
- 初期化スクリプト（`./scripts/setup-admin.sh`）により、確実に同じAPIキーが設定される
- APIキーは開発用に固定値を使用

**API使用例:**
```bash
curl -H "X-Redmine-API-Key: 048110ce3e4a78b218aede2826b01fbc90dff412" \
     http://localhost:3000/issues.json
```

## コア開発ルール

1. パッケージ管理
   - uvのみを使用し、pipは絶対に使わない
   - インストール: `uv add package`
   - ツール実行: `uv run tool`
   - アップグレード: `uv add --dev package --upgrade-package package`
   - 禁止事項: `uv pip install`、`@latest`構文

2. コード品質
   - すべてのコードに型ヒントが必要
   - パブリックAPIには必ずdocstringを記述
   - 関数は集中的で小さくする
   - 既存のパターンに正確に従う
   - 行の長さ: 最大88文字

3. テスト要件
   - フレームワーク: `uv run --frozen pytest`
   - 非同期テスト: asyncioではなくanyioを使用
   - カバレッジ: エッジケースとエラーのテスト
   - 新機能にはテストが必要
   - バグ修正にはリグレッションテストが必要

- `co-authored-by`や類似の記述は絶対に言及しない。特に、コミットメッセージやPRの作成に使用したツールには言及しない。

## コミット

**基本方針:**
- 論理的なまとまりごとにコミットを実行
- 日本語のConventional Commitフォーマットを使用

**フォーマット:**
```
<type>: <description>

[optional body]
```

**タイプ:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードフォーマット
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: ビルド・設定変更

**例:**
```
feat: Redmineバーンダウンチャート作成機能を追加

- チケット工数データの取得APIを実装
- チャート描画ロジックを追加
- 日付範囲指定機能を実装
```

## プルリクエスト

- 何が変更されたかの詳細なメッセージを作成する。解決しようとする問題の高レベルな説明と、それがどのように解決されるかに焦点を当てる。明確さを追加しない限り、コードの詳細には立ち入らない。
- `co-authored-by`や類似の記述は絶対に言及しない。特に、コミットメッセージやPRの作成に使用したツールには言及しない。

## Pythonツール

## コードフォーマット

1. Ruff
   - フォーマット: `uv run --frozen ruff format .`
   - チェック: `uv run --frozen ruff check .`
   - 修正: `uv run --frozen ruff check . --fix`
   - 重要な問題:
     - 行の長さ（88文字）
     - インポートのソート（I001）
     - 未使用のインポート
   - 行の折り返し:
     - 文字列: 括弧を使用
     - 関数呼び出し: 適切なインデントでマルチライン
     - インポート: 複数行に分割

2. 型チェック
   - ツール: `uv run --frozen pyright`
   - 要件:
     - Optionalの明示的なNoneチェック
     - 文字列の型の絞り込み
     - チェックが通ればバージョン警告は無視可能

3. Pre-commit
   - 設定: `.pre-commit-config.yaml`
   - 実行: git commitで実行
   - ツール: Prettier（YAML/JSON）、Ruff（Python）
   - Ruffアップデート:
     - PyPIバージョンをチェック
     - 設定のrevを更新
     - 設定を最初にコミット

## エラー解決

1. CI失敗
   - 修正順序:
     1. フォーマット
     2. 型エラー
     3. リント
   - 型エラー:
     - 完全な行コンテキストを取得
     - Optional型をチェック
     - 型の絞り込みを追加
     - 関数シグネチャを検証

2. 一般的な問題
   - 行の長さ:
     - 括弧で文字列を分割
     - マルチライン関数呼び出し
     - インポートを分割
   - 型:
     - Noneチェックを追加
     - 文字列型を絞り込み
     - 既存パターンに合わせる
   - Pytest:
     - テストでanyio pytestマークが見つからない場合、pytestの実行コマンドの先頭にPYTEST_DISABLE_PLUGIN_AUTOLOAD=""を追加してみる例:
       `PYTEST_DISABLE_PLUGIN_AUTOLOAD="" uv run --frozen pytest`

3. ベストプラクティス
   - コミット前にgit statusをチェック
   - 型チェック前にフォーマッターを実行
   - 変更を最小限に保つ
   - 既存パターンに従う
   - パブリックAPIを文書化
   - 徹底的にテスト
