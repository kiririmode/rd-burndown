#!/bin/bash

set -e  # エラー時に停止

echo "🚀 Redmineテスト環境の完全セットアップを開始..."

API_KEY="048110ce3e4a78b218aede2826b01fbc90dff412"  # pragma: allowlist secret
BASE_URL="http://localhost:3000"

echo ""
echo "1️⃣ Redmineコンテナの起動..."
docker compose up -d

echo ""
echo "2️⃣ 管理者設定の実行..."
./scripts/setup-admin.sh

echo ""
echo "3️⃣ 基本マスターデータの作成..."
# SQLでマスターデータを作成
docker exec redmine-db psql -U redmine -d redmine -c "
-- トラッカーの作成
INSERT INTO trackers (name, description, default_status_id, is_in_chlog, position, is_in_roadmap) VALUES
('Bug', 'バグ修正', 1, true, 1, true),
('Feature', '新機能', 1, true, 2, true),
('Support', 'サポート', 1, true, 3, false)
ON CONFLICT DO NOTHING;

-- チケットステータスの作成
INSERT INTO issue_statuses (name, is_closed, position, default_done_ratio) VALUES
('New', false, 1, 0),
('In Progress', false, 2, 30),
('Resolved', false, 3, 90),
('Closed', true, 4, 100)
ON CONFLICT DO NOTHING;

-- 優先度の作成
INSERT INTO enumerations (name, type, position, is_default, active) VALUES
('Low', 'IssuePriority', 1, false, true),
('Normal', 'IssuePriority', 2, true, true),
('High', 'IssuePriority', 3, false, true),
('Urgent', 'IssuePriority', 4, false, true)
ON CONFLICT DO NOTHING;

-- 管理者ロールの作成
INSERT INTO roles (name, assignable, builtin, permissions, position) VALUES
('Manager', true, 0, '---
- :add_project
- :edit_project
- :close_project
- :delete_project
- :select_project_modules
- :manage_members
- :manage_versions
- :add_subprojects
- :view_issues
- :add_issues
- :edit_issues
- :copy_issues
- :manage_issue_relations
- :manage_subtasks
- :set_issues_private
- :set_own_issues_private
- :add_issue_notes
- :edit_issue_notes
- :edit_own_issue_notes
- :view_private_notes
- :set_notes_private
- :delete_issues
- :view_issue_watchers
- :add_issue_watchers
- :delete_issue_watchers
- :import_issues
- :manage_public_queries
- :save_queries
- :view_gantt
- :view_calendar
- :log_time
- :view_time_entries
- :edit_time_entries
- :edit_own_time_entries
- :manage_project_activities
- :view_news
- :manage_news
- :comment_news
- :view_documents
- :add_documents
- :edit_documents
- :delete_documents
- :view_wiki_pages
- :view_wiki_edits
- :export_wiki_pages
- :edit_wiki_pages
- :rename_wiki_pages
- :delete_wiki_pages
- :delete_wiki_pages_attachments
- :protect_wiki_pages
- :manage_wiki
- :view_messages
- :add_messages
- :edit_messages
- :edit_own_messages
- :delete_messages
- :delete_own_messages
- :manage_boards
- :view_files
- :manage_files
- :view_changesets
- :browse_repository
- :manage_repository
- :commit_access
- :manage_related_issues
- :manage_subtasks', 1)
ON CONFLICT DO NOTHING;
" 2>/dev/null || echo "⚠️  一部のマスターデータは既に存在します"

echo ""
echo "4️⃣ テストプロジェクトの作成..."
docker exec redmine curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "X-Redmine-API-Key: $API_KEY" \
    -d '{
        "project": {
            "name": "テストプロジェクト",
            "identifier": "test-project",
            "description": "バーンダウンチャート用のテストプロジェクト",
            "is_public": false,
            "enabled_module_names": ["issue_tracking", "time_tracking", "versions"]
        }
    }' \
    "$BASE_URL/projects.json" > /dev/null

# プロジェクトの開始日・終了日を設定（バーンダウンチャート用）
docker exec redmine-db psql -U redmine -d redmine -c "
UPDATE projects
SET created_on = '2025-08-10 08:00:00'::timestamp,
    updated_on = '2025-08-10 08:00:00'::timestamp
WHERE identifier = 'test-project';
" 2>/dev/null || echo "⚠️  プロジェクト日付設定に失敗"

# プロジェクトとトラッカーの関連付け、管理者のメンバー登録
docker exec redmine-db psql -U redmine -d redmine -c "
-- プロジェクトにトラッカーを関連付け
INSERT INTO projects_trackers (project_id, tracker_id) VALUES (1, 1), (1, 2), (1, 3)
ON CONFLICT DO NOTHING;

-- 管理者をプロジェクトメンバーに追加
INSERT INTO members (user_id, project_id, created_on, mail_notification) VALUES (1, 1, NOW(), false)
ON CONFLICT DO NOTHING;

-- メンバーに管理者ロールを付与
INSERT INTO member_roles (member_id, role_id, inherited_from) VALUES (1, 3, NULL)
ON CONFLICT DO NOTHING;
" 2>/dev/null || echo "⚠️  プロジェクト関連設定は既に存在します"

echo ""
echo "5️⃣ バージョンの作成..."
docker exec redmine curl -s -X POST -H "Content-Type: application/json" -H "X-Redmine-API-Key: $API_KEY" \
    -d '{"version": {"name": "v1.0.0", "description": "初回リリースバージョン", "due_date": "2025-09-30"}}' \
    "$BASE_URL/projects/test-project/versions.json" > /dev/null

docker exec redmine curl -s -X POST -H "Content-Type: application/json" -H "X-Redmine-API-Key: $API_KEY" \
    -d '{"version": {"name": "v1.1.0", "description": "機能追加バージョン", "due_date": "2025-10-31"}}' \
    "$BASE_URL/projects/test-project/versions.json" > /dev/null

docker exec redmine curl -s -X POST -H "Content-Type: application/json" -H "X-Redmine-API-Key: $API_KEY" \
    -d '{"version": {"name": "v2.0.0", "description": "メジャーアップデートバージョン", "due_date": "2025-12-31"}}' \
    "$BASE_URL/projects/test-project/versions.json" > /dev/null

echo ""
echo "6️⃣ テストチケットの作成..."
./scripts/create_test_issues.sh > /dev/null

echo ""
echo "7️⃣ バーンダウンチャート用テストデータの作成..."
./scripts/create_burndown_test_data.sh > /dev/null

echo ""
echo "8️⃣ rd-burndownプロジェクト同期..."
# DevContainer環境でのネットワーク接続設定
export RD_REDMINE_URL="http://172.17.0.1:3000"
export RD_REDMINE_API_KEY="$API_KEY"

# プロジェクト同期実行
if command -v uv >/dev/null 2>&1; then
    echo "   rd-burndownプロジェクト同期を実行中..."
    uv run rd-burndown project sync 1 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ プロジェクト同期完了"
    else
        echo "   ⚠️  プロジェクト同期で警告が発生（手動同期を推奨）"
        echo "   手動同期コマンド: export RD_REDMINE_URL=\"http://172.17.0.1:3000\" && export RD_REDMINE_API_KEY=\"$API_KEY\" && uv run rd-burndown project sync 1"
    fi
else
    echo "   ⚠️  uvコマンドが見つかりません。手動でプロジェクト同期を実行してください"
    echo "   手動同期コマンド: export RD_REDMINE_URL=\"http://172.17.0.1:3000\" && export RD_REDMINE_API_KEY=\"$API_KEY\" && uv run rd-burndown project sync 1"
fi

echo ""
echo "9️⃣ セットアップ完了テストを実行中..."

# テスト関数の定義
test_redmine_connection() {
    echo "   🔍 Redmine接続テスト..."
    if docker exec redmine curl -s -f "$BASE_URL" > /dev/null 2>&1; then
        echo "   ✅ Redmine Web UI接続OK"
        return 0
    else
        echo "   ❌ Redmine Web UI接続NG"
        return 1
    fi
}

test_api_access() {
    echo "   🔍 API接続テスト..."
    API_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/users/current.json" 2>/dev/null)
    if echo "$API_RESPONSE" | grep -q "user"; then
        echo "   ✅ API接続OK（管理者認証成功）"
        return 0
    else
        echo "   ❌ API接続NG（APIキー認証失敗）"
        return 1
    fi
}

test_project_creation() {
    echo "   🔍 プロジェクト作成テスト..."
    PROJECT_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project.json" 2>/dev/null)
    if echo "$PROJECT_RESPONSE" | grep -q "test-project"; then
        echo "   ✅ テストプロジェクト作成OK"
        return 0
    else
        echo "   ❌ テストプロジェクト作成NG"
        return 1
    fi
}

test_versions_creation() {
    echo "   🔍 バージョン作成テスト..."
    VERSIONS_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/versions.json" 2>/dev/null)
    VERSION_COUNT=$(echo "$VERSIONS_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('versions', [])))" 2>/dev/null || echo "0")

    if [ "$VERSION_COUNT" -ge 3 ]; then
        echo "   ✅ バージョン作成OK（$VERSION_COUNT件）"
        return 0
    else
        echo "   ❌ バージョン作成NG（期待値: 3件、実際: $VERSION_COUNT件）"
        return 1
    fi
}

test_issues_creation() {
    echo "   🔍 チケット作成テスト..."
    ISSUES_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json" 2>/dev/null)
    ISSUE_COUNT=$(echo "$ISSUES_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null || echo "0")

    if [ "$ISSUE_COUNT" -ge 8 ]; then
        echo "   ✅ チケット作成OK（$ISSUE_COUNT件）"
        return 0
    else
        echo "   ❌ チケット作成NG（期待値: 8件以上、実際: $ISSUE_COUNT件）"
        return 1
    fi
}

test_estimated_hours() {
    echo "   🔍 予定工数設定テスト..."
    ISSUES_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json" 2>/dev/null)
    TOTAL_HOURS=$(echo "$ISSUES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = sum(float(issue.get('estimated_hours', 0)) for issue in data.get('issues', []) if issue.get('estimated_hours'))
    print(f'{total:.1f}')
except:
    print('0.0')
" 2>/dev/null || echo "0.0")

    HOURS_CHECK=$(python3 -c "print('1' if float('$TOTAL_HOURS') > 100 else '0')" 2>/dev/null || echo "0")
    if [ "$HOURS_CHECK" = "1" ]; then
        echo "   ✅ 予定工数設定OK（合計: ${TOTAL_HOURS}時間）"
        return 0
    else
        echo "   ❌ 予定工数設定NG（期待値: 100時間以上、実際: ${TOTAL_HOURS}時間）"
        return 1
    fi
}

test_version_linking() {
    echo "   🔍 バージョン紐づけテスト..."
    ISSUES_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json?include=fixed_version" 2>/dev/null)
    LINKED_COUNT=$(echo "$ISSUES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    linked = sum(1 for issue in data.get('issues', []) if issue.get('fixed_version'))
    print(linked)
except:
    print(0)
" 2>/dev/null || echo "0")

    if [ "$LINKED_COUNT" -ge 8 ]; then
        echo "   ✅ バージョン紐づけOK（$LINKED_COUNT件）"
        return 0
    else
        echo "   ❌ バージョン紐づけNG（期待値: 8件以上、実際: $LINKED_COUNT件）"
        return 1
    fi
}

# 全テストの実行
FAILED_TESTS=0

test_redmine_connection || FAILED_TESTS=$((FAILED_TESTS + 1))
test_api_access || FAILED_TESTS=$((FAILED_TESTS + 1))
test_project_creation || FAILED_TESTS=$((FAILED_TESTS + 1))
test_versions_creation || FAILED_TESTS=$((FAILED_TESTS + 1))
test_issues_creation || FAILED_TESTS=$((FAILED_TESTS + 1))
test_estimated_hours || FAILED_TESTS=$((FAILED_TESTS + 1))
test_version_linking || FAILED_TESTS=$((FAILED_TESTS + 1))

echo ""
if [ $FAILED_TESTS -eq 0 ]; then
    echo "🎉 全テストが成功しました！Redmineテスト環境のセットアップが完了しました！"
    SETUP_STATUS="✅ 成功"
else
    echo "⚠️  $FAILED_TESTS 個のテストが失敗しました。セットアップに問題がある可能性があります。"
    SETUP_STATUS="❌ 失敗（$FAILED_TESTS 個のテスト失敗）"
fi

echo ""
echo "📋 セットアップ結果サマリー:"

# 最終結果確認
ISSUES_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json" 2>/dev/null)
ISSUE_COUNT=$(echo "$ISSUES_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null || echo "0")
TOTAL_HOURS=$(echo "$ISSUES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = sum(float(issue.get('estimated_hours', 0)) for issue in data.get('issues', []) if issue.get('estimated_hours'))
    print(f'{total:.1f}')
except:
    print('0.0')
" 2>/dev/null || echo "0.0")

echo "   📁 プロジェクト: テストプロジェクト (test-project)"
echo "   🏷️  バージョン: v1.0.0, v1.1.0, v2.0.0"
echo "   🎫 チケット数: $ISSUE_COUNT件"
echo "   ⏱️  総予定工数: ${TOTAL_HOURS}時間"
echo "   🧪 テスト結果: $SETUP_STATUS"
echo ""
echo "🔗 アクセス情報:"
echo "   Web UI: http://localhost:3000"
echo "   ログイン: admin / admin"
echo "   APIキー: $API_KEY"
echo ""
if [ $FAILED_TESTS -eq 0 ]; then
    echo "📊 バーンダウンチャート開発の準備が整いました！"
    echo "   プロジェクト: http://localhost:3000/projects/test-project"
    echo "   チケット一覧: http://localhost:3000/projects/test-project/issues"
    echo "   バージョン一覧: http://localhost:3000/projects/test-project/versions"
    echo ""
    echo "🎯 バーンダウンチャート生成コマンド:"
    echo "   export RD_REDMINE_URL=\"http://172.17.0.1:3000\""
    echo "   export RD_REDMINE_API_KEY=\"$API_KEY\""
    echo "   uv run rd-burndown chart burndown 1 --output burndown_chart.png"
    exit 0
else
    echo "🔧 問題解決のヒント:"
    echo "   1. コンテナの状態確認: docker ps"
    echo "   2. Redmineログ確認: docker logs redmine"
    echo "   3. 手動でWeb UIにアクセスして設定確認"
    echo "   4. 環境をリセットして再実行: docker compose down -v && ./scripts/setup_complete_test_environment.sh"
    exit 1
fi
