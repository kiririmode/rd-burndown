#!/bin/bash

echo "📈 バーンダウンチャート用のテストデータを作成中..."

# SQLで直接チケットステータスと履歴を作成
docker exec redmine-db psql -U redmine -d redmine -c "
-- 2025-08-10: 最初のチケットを進行中に (ユーザー認証機能、データベース設計)
UPDATE issues SET status_id = 2, updated_on = '2025-08-10 09:00:00' WHERE id = 18;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 18, 'Issue', '2025-08-10 09:00:00', 'ステータスを「進行中」に変更');

UPDATE issues SET status_id = 2, updated_on = '2025-08-10 14:00:00' WHERE id = 19;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 19, 'Issue', '2025-08-10 14:00:00', 'ステータスを「進行中」に変更');

-- 2025-08-12: セキュリティ脆弱性修正を解決
UPDATE issues SET status_id = 3, updated_on = '2025-08-12 10:30:00' WHERE id = 20;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 20, 'Issue', '2025-08-12 10:30:00', 'ステータスを「解決」に変更');

-- 2025-08-13: パスワードリセット機能を進行中に
UPDATE issues SET status_id = 2, updated_on = '2025-08-13 11:00:00' WHERE id = 21;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 21, 'Issue', '2025-08-13 11:00:00', 'ステータスを「進行中」に変更');

-- 2025-08-14: セキュリティ脆弱性修正を完了、データベース設計を解決
UPDATE issues SET status_id = 4, updated_on = '2025-08-14 16:00:00' WHERE id = 20;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 20, 'Issue', '2025-08-14 16:00:00', 'ステータスを「完了」に変更');

UPDATE issues SET status_id = 3, updated_on = '2025-08-14 17:30:00' WHERE id = 19;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 19, 'Issue', '2025-08-14 17:30:00', 'ステータスを「解決」に変更');

-- 2025-08-15: API仕様書作成を進行中に、ユーザー認証機能を解決
UPDATE issues SET status_id = 2, updated_on = '2025-08-15 09:15:00' WHERE id = 22;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 22, 'Issue', '2025-08-15 09:15:00', 'ステータスを「進行中」に変更');

UPDATE issues SET status_id = 3, updated_on = '2025-08-15 15:45:00' WHERE id = 18;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 18, 'Issue', '2025-08-15 15:45:00', 'ステータスを「解決」に変更');

-- 2025-08-16: データベース設計完了、API仕様書解決
UPDATE issues SET status_id = 4, updated_on = '2025-08-16 10:00:00' WHERE id = 19;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 19, 'Issue', '2025-08-16 10:00:00', 'ステータスを「完了」に変更');

UPDATE issues SET status_id = 3, updated_on = '2025-08-16 14:20:00' WHERE id = 22;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 22, 'Issue', '2025-08-16 14:20:00', 'ステータスを「解決」に変更');

-- 2025-08-17 (今日): ユーザー認証機能完了、API仕様書完了、パスワードリセット機能解決
UPDATE issues SET status_id = 4, updated_on = '2025-08-17 09:30:00' WHERE id = 18;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 18, 'Issue', '2025-08-17 09:30:00', 'ステータスを「完了」に変更');

UPDATE issues SET status_id = 4, updated_on = '2025-08-17 11:00:00' WHERE id = 22;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 22, 'Issue', '2025-08-17 11:00:00', 'ステータスを「完了」に変更');

UPDATE issues SET status_id = 3, updated_on = '2025-08-17 13:15:00' WHERE id = 21;
INSERT INTO journals (user_id, journalized_id, journalized_type, created_on, notes)
VALUES (1, 21, 'Issue', '2025-08-17 13:15:00', 'ステータスを「解決」に変更');
"

echo ""
echo "📊 作成されたテストデータを確認中..."

# 現在のチケット状況を確認
docker exec redmine-db psql -U redmine -d redmine -c "
SELECT
    i.id,
    i.subject,
    s.name as status_name,
    i.estimated_hours,
    i.updated_on::date as last_updated
FROM issues i
JOIN issue_statuses s ON i.status_id = s.id
WHERE i.project_id = 1
ORDER BY i.id;
"

echo ""
echo "📈 チケット履歴の確認..."

# チケット履歴を確認
docker exec redmine-db psql -U redmine -d redmine -c "
SELECT
    j.journalized_id as issue_id,
    i.subject,
    j.created_on::date as change_date,
    j.notes
FROM journals j
JOIN issues i ON j.journalized_id = i.id
WHERE j.journalized_type = 'Issue'
  AND i.project_id = 1
  AND j.notes LIKE '%ステータス%'
ORDER BY j.created_on;
"

echo ""
echo "📊 日別進捗サマリー（バーンダウンチャート用）..."

# バーンダウンチャート用の日別データ
docker exec redmine-db psql -U redmine -d redmine -c "
WITH daily_completion AS (
    SELECT
        j.created_on::date as completion_date,
        SUM(i.estimated_hours) as completed_hours
    FROM journals j
    JOIN issues i ON j.journalized_id = i.id
    WHERE j.journalized_type = 'Issue'
      AND i.project_id = 1
      AND j.notes LIKE '%完了%'
    GROUP BY j.created_on::date
    ORDER BY completion_date
),
total_hours AS (
    SELECT SUM(estimated_hours) as total FROM issues WHERE project_id = 1
)
SELECT
    completion_date,
    completed_hours,
    (SELECT total FROM total_hours) as total_hours,
    (SELECT total FROM total_hours) - SUM(completed_hours) OVER (ORDER BY completion_date) as remaining_hours
FROM daily_completion;
"

echo ""
echo "🎉 バーンダウンチャート用のテストデータ作成完了！"
echo "📊 複数の日付にわたる進捗データが準備されました。"
