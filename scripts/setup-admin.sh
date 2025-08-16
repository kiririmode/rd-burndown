#!/bin/bash

echo "🚀 Redmine管理者セットアップを開始..."

# Redmineコンテナが起動するのを待つ
echo "⏳ Redmineの起動を待機中..."
sleep 30

# Redmineコンテナ内でRubyスクリプトを実行
echo "📝 初期化スクリプトをコピー中..."
docker cp scripts/init-redmine.rb redmine:/tmp/init-redmine.rb

echo "🔧 管理者ユーザーとAPIキーを設定中..."
docker exec redmine bash -c "cd /usr/src/redmine && RAILS_ENV=production ruby /tmp/init-redmine.rb"

echo "✅ セットアップ完了！"
echo "📋 認証情報:"
echo "   ログイン: admin"
echo "   パスワード: admin" 
echo "   APIキー: 048110ce3e4a78b218aede2826b01fbc90dff412"