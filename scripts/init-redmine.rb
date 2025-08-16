#!/usr/bin/env ruby

# Redmine初期化スクリプト
# 管理者ユーザーの作成とAPIキーの固定設定

puts "🚀 Redmine初期化スクリプトを開始..."

# Redmine環境の読み込み
require '/usr/src/redmine/config/environment'

# 固定のAPIキー（開発環境用）
FIXED_API_KEY = '048110ce3e4a78b218aede2826b01fbc90dff412'

begin
  # 管理者ユーザーの確認・作成
  admin = User.where(login: 'admin').first
  
  if admin.nil?
    puts "📝 管理者ユーザーを作成中..."
    admin = User.new(
      login: 'admin',
      firstname: 'Redmine',
      lastname: 'Admin',
      mail: 'admin@example.com',
      language: 'ja'
    )
    admin.password = 'admin'
    admin.password_confirmation = 'admin'
    admin.admin = true
    admin.status = User::STATUS_ACTIVE
    
    if admin.save
      puts "✅ 管理者ユーザーを作成しました"
    else
      puts "❌ 管理者ユーザー作成に失敗:"
      admin.errors.full_messages.each { |msg| puts "  - #{msg}" }
      exit 1
    end
  else
    puts "✅ 管理者ユーザーが既に存在します (ID: #{admin.id})"
  end
  
  # APIキーの設定
  existing_token = Token.where(user_id: admin.id, action: 'api').first
  
  if existing_token.nil?
    puts "🔑 APIキーを作成中..."
    token = Token.new(
      user_id: admin.id,
      action: 'api',
      value: FIXED_API_KEY
    )
    
    if token.save
      puts "✅ APIキーを作成しました: #{FIXED_API_KEY}"
    else
      puts "❌ APIキー作成に失敗"
      exit 1
    end
  elsif existing_token.value != FIXED_API_KEY
    puts "🔄 APIキーを固定値に更新中..."
    existing_token.value = FIXED_API_KEY
    existing_token.save!
    puts "✅ APIキーを更新しました: #{FIXED_API_KEY}"
  else
    puts "✅ APIキーは既に設定済みです: #{existing_token.value}"
  end
  
  puts "🎉 初期化完了!"
  puts "📋 認証情報:"
  puts "   ログイン: admin"
  puts "   パスワード: admin"
  puts "   APIキー: #{FIXED_API_KEY}"
  
rescue => e
  puts "❌ エラーが発生しました: #{e.message}"
  puts e.backtrace.first(5).join("\n")
  exit 1
end