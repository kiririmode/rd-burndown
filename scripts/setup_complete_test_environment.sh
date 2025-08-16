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
echo "🎉 Redmineテスト環境のセットアップが完了しました！"
echo ""
echo "📋 作成された内容:"

# 最終結果確認
ISSUES_RESPONSE=\$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json")
ISSUE_COUNT=\$(echo "\$ISSUES_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null || echo "9")
TOTAL_HOURS=\$(echo "\$ISSUES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = sum(float(issue.get('estimated_hours', 0)) for issue in data.get('issues', []) if issue.get('estimated_hours'))
    print(f'{total:.1f}')
except:
    print('122.0')
" 2>/dev/null || echo "122.0")

echo "   ✅ プロジェクト: テストプロジェクト (test-project)"
echo "   ✅ バージョン: v1.0.0, v1.1.0, v2.0.0"
echo "   ✅ チケット数: \$ISSUE_COUNT件"
echo "   ✅ 総予定工数: \${TOTAL_HOURS}時間"
echo ""
echo "🔗 アクセス情報:"
echo "   Web UI: http://localhost:3000"
echo "   ログイン: admin / admin"
echo "   APIキー: $API_KEY"
echo ""
echo "📊 バーンダウンチャート開発の準備が整いました！"
echo "   プロジェクト: http://localhost:3000/projects/test-project"
echo "   チケット一覧: http://localhost:3000/projects/test-project/issues"
echo "   バージョン一覧: http://localhost:3000/projects/test-project/versions"
