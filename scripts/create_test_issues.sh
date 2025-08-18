#!/bin/bash

echo "🎫 テストチケットを作成中..."

API_KEY="048110ce3e4a78b218aede2826b01fbc90dff412"  # pragma: allowlist secret
BASE_URL="http://localhost:3000"

# 既存のテストチケットをクリア（重複回避のため）
echo "🧹 既存チケットのクリア..."
docker exec redmine-db psql -U redmine -d redmine -c "
DELETE FROM issues WHERE project_id = 1;
DELETE FROM journals WHERE journalized_type = 'Issue' AND journalized_id NOT IN (SELECT id FROM issues);
" 2>/dev/null || echo "⚠️  チケットクリアで警告が発生しましたが続行します"

# チケットデータ配列
create_issue() {
    local subject="$1"
    local description="$2"
    local tracker_id="$3"
    local status_id="$4"
    local priority_id="$5"
    local estimated_hours="$6"
    local fixed_version_id="$7"

    RESPONSE=$(docker exec redmine curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "X-Redmine-API-Key: $API_KEY" \
        -d "{
            \"issue\": {
                \"subject\": \"$subject\",
                \"description\": \"$description\",
                \"tracker_id\": $tracker_id,
                \"status_id\": $status_id,
                \"priority_id\": $priority_id,
                \"estimated_hours\": $estimated_hours,
                \"fixed_version_id\": $fixed_version_id
            }
        }" \
        "$BASE_URL/projects/test-project/issues.json")

    if echo "$RESPONSE" | grep -q "issue"; then
        ISSUE_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['issue']['id'])" 2>/dev/null || echo "作成済み")
        echo "✅ チケット #$ISSUE_ID - $subject (予定工数: ${estimated_hours}h)"
    else
        echo "❌ チケット '$subject' の作成に失敗: $RESPONSE"
    fi
}

echo "作成対象のチケット:"

# v1.0.0 向けチケット
create_issue "ユーザー認証機能の実装" "ログイン・ログアウト機能を実装する" 2 1 6 16.0 1
create_issue "データベース設計" "ユーザーテーブルと関連テーブルの設計" 2 2 7 8.0 1
create_issue "セキュリティ脆弱性の修正" "XSS攻撃に対する対策の実装" 1 3 7 4.0 1

# v1.1.0 向けチケット
create_issue "パスワードリセット機能" "メール経由でのパスワードリセット機能" 2 1 6 12.0 2
create_issue "API仕様書の作成" "RESTful APIの仕様書をOpenAPIで作成" 3 1 6 6.0 2

# v2.0.0 向けチケット
create_issue "ユーザー管理機能の改善" "管理者による一括ユーザー操作機能" 2 1 6 20.0 3
create_issue "パフォーマンス最適化" "データベースクエリの最適化とキャッシュ実装" 2 2 7 24.0 3
create_issue "モバイル対応" "レスポンシブデザインの実装" 2 1 6 32.0 3

echo ""
echo "📅 チケット作成日を2025-08-10に統一中..."

# 全チケットの作成日を8/10に設定（バーンダウンチャート用）
docker exec redmine-db psql -U redmine -d redmine -c "
UPDATE issues
SET created_on = '2025-08-10 08:00:00'::timestamp,
    updated_on = '2025-08-10 08:00:00'::timestamp
WHERE project_id = 1;
" 2>/dev/null || echo "⚠️  チケット日付設定で警告が発生"

echo ""
echo "🎉 テストチケットの作成が完了しました！"

# 作成結果の確認
echo ""
echo "📋 作成結果を確認中..."
ISSUES_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json")
ISSUE_COUNT=$(echo "$ISSUES_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_count', 0))" 2>/dev/null || echo "0")
echo "✅ 総チケット数: $ISSUE_COUNT"

# 総工数計算
TOTAL_HOURS=$(echo "$ISSUES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = sum(float(issue.get('estimated_hours', 0)) for issue in data.get('issues', []) if issue.get('estimated_hours'))
    print(f'{total:.1f}')
except:
    print('0.0')
" 2>/dev/null || echo "0.0")
echo "✅ 総予定工数: ${TOTAL_HOURS}時間"

# バージョン別工数
echo ""
echo "📊 バージョン別予定工数:"
echo "$ISSUES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    by_version = {}
    for issue in data.get('issues', []):
        if issue.get('fixed_version') and issue.get('estimated_hours'):
            version_name = issue['fixed_version']['name']
            hours = float(issue['estimated_hours'])
            by_version[version_name] = by_version.get(version_name, 0) + hours

    for version, hours in sorted(by_version.items()):
        print(f'   {version}: {hours:.1f}時間')
except:
    pass
" 2>/dev/null

echo ""
echo "🔗 確認用URL:"
echo "   プロジェクト: http://localhost:3000/projects/test-project"
echo "   チケット一覧: http://localhost:3000/projects/test-project/issues"
echo "   バージョン一覧: http://localhost:3000/projects/test-project/versions"
