#!/bin/bash

echo "📈 チケットの進捗状況を更新中..."

API_KEY="048110ce3e4a78b218aede2826b01fbc90dff412"  # pragma: allowlist secret
BASE_URL="http://localhost:3000"

# チケットのステータス更新関数
update_issue_status() {
    local issue_id="$1"
    local status_id="$2"
    local status_name="$3"
    local update_date="$4"

    echo "  🔄 チケット #$issue_id を $status_name に変更..."

    # チケットのステータス更新
    RESPONSE=$(docker exec redmine curl -s -X PUT \
        -H "Content-Type: application/json" \
        -H "X-Redmine-API-Key: $API_KEY" \
        -d "{
            \"issue\": {
                \"status_id\": $status_id
            }
        }" \
        "$BASE_URL/issues/$issue_id.json")

    # 更新日時をSQLで直接変更（時系列データのため）
    if [ -n "$update_date" ]; then
        docker exec redmine-db psql -U redmine -d redmine -c "
            UPDATE journals
            SET created_on = '$update_date'::timestamp
            WHERE journalized_id = $issue_id
            AND journalized_type = 'Issue'
            ORDER BY id DESC
            LIMIT 1;
        " 2>/dev/null
    fi

    if echo "$RESPONSE" | grep -q "errors" || [ -z "$RESPONSE" ]; then
        echo "    ✅ チケット #$issue_id 更新完了"
    else
        echo "    ❌ チケット #$issue_id 更新失敗: $RESPONSE"
    fi
}

# 最新のチケットIDを取得
echo "🔍 最新のチケットIDを取得中..."
LATEST_ISSUES=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json?limit=100")

# チケットIDを動的に取得（新しい順）
AUTH_ID=$(echo "$LATEST_ISSUES" | python3 -c "import sys, json; data=json.load(sys.stdin); print([i['id'] for i in data['issues'] if 'ユーザー認証機能' in i['subject']][0])" 2>/dev/null)
DB_ID=$(echo "$LATEST_ISSUES" | python3 -c "import sys, json; data=json.load(sys.stdin); print([i['id'] for i in data['issues'] if 'データベース設計' in i['subject']][0])" 2>/dev/null)
SEC_ID=$(echo "$LATEST_ISSUES" | python3 -c "import sys, json; data=json.load(sys.stdin); print([i['id'] for i in data['issues'] if 'セキュリティ脆弱性' in i['subject']][0])" 2>/dev/null)
PASS_ID=$(echo "$LATEST_ISSUES" | python3 -c "import sys, json; data=json.load(sys.stdin); print([i['id'] for i in data['issues'] if 'パスワードリセット' in i['subject']][0])" 2>/dev/null)
API_ID=$(echo "$LATEST_ISSUES" | python3 -c "import sys, json; data=json.load(sys.stdin); print([i['id'] for i in data['issues'] if 'API仕様書' in i['subject']][0])" 2>/dev/null)

echo "🎯 取得したチケットID: 認証=$AUTH_ID, DB=$DB_ID, セキュリティ=$SEC_ID, パスワード=$PASS_ID, API=$API_ID"
echo ""
echo "🎯 過去日付での進捗更新を実行..."

# 2025-08-10: 最初のチケットを進行中に
update_issue_status $AUTH_ID 2 "In Progress" "2025-08-10 09:00:00"
update_issue_status $DB_ID 2 "In Progress" "2025-08-10 14:00:00"

# 2025-08-12: 小さいチケットを解決
update_issue_status $SEC_ID 3 "Resolved" "2025-08-12 10:30:00"

# 2025-08-13: さらにチケットを進行中に
update_issue_status $PASS_ID 2 "In Progress" "2025-08-13 11:00:00"

# 2025-08-14: いくつかのチケットを解決・完了
update_issue_status $SEC_ID 4 "Closed" "2025-08-14 16:00:00"  # セキュリティ脆弱性修正完了
update_issue_status $DB_ID 3 "Resolved" "2025-08-14 17:30:00"  # データベース設計解決

# 2025-08-15: さらに進捗
update_issue_status $API_ID 2 "In Progress" "2025-08-15 09:15:00"  # API仕様書作成開始
update_issue_status $AUTH_ID 3 "Resolved" "2025-08-15 15:45:00"  # ユーザー認証機能解決

# 2025-08-16: 完了チケット追加
update_issue_status $DB_ID 4 "Closed" "2025-08-16 10:00:00"  # データベース設計完了
update_issue_status $API_ID 3 "Resolved" "2025-08-16 14:20:00"  # API仕様書解決

# 2025-08-17 (今日): 最新の進捗
update_issue_status $AUTH_ID 4 "Closed" "2025-08-17 09:30:00"  # ユーザー認証機能完了
update_issue_status $API_ID 4 "Closed" "2025-08-17 11:00:00"  # API仕様書完了
update_issue_status $PASS_ID 3 "Resolved" "2025-08-17 13:15:00"  # パスワードリセット機能解決

echo ""
echo "📊 進捗状況の確認..."

# 現在のチケット状況を確認
ISSUES_RESPONSE=$(docker exec redmine curl -s -H "X-Redmine-API-Key: $API_KEY" "$BASE_URL/projects/test-project/issues.json?limit=100&include=status")

echo ""
echo "✅ 更新完了！現在のチケット状況:"
echo "$ISSUES_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
status_counts = {}
completed_hours = 0
total_hours = 0

for issue in data.get('issues', []):
    status_name = issue.get('status', {}).get('name', 'Unknown')
    hours = float(issue.get('estimated_hours', 0))
    total_hours += hours

    if status_name in status_counts:
        status_counts[status_name] += 1
    else:
        status_counts[status_name] = 1

    # 完了状態（Closed）の工数を計算
    if status_name == 'Closed':
        completed_hours += hours

print(f'ステータス別チケット数:')
for status, count in sorted(status_counts.items()):
    print(f'  {status}: {count}件')

print(f'\\n工数サマリー:')
print(f'  総予定工数: {total_hours:.1f}時間')
print(f'  完了工数: {completed_hours:.1f}時間')
print(f'  残り工数: {total_hours - completed_hours:.1f}時間')
print(f'  進捗率: {(completed_hours/total_hours)*100:.1f}%')
"

echo ""
echo "🎉 バーンダウンチャート用のテストデータ準備完了！"
echo "📈 時系列の進捗データが作成されました。"
