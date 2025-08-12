# slack2cal

📅 **Slack画像からGoogle Calendarへの自動連携アプリ**

slack2calは、Slackチャンネルにアップロードされた日付入りスクリーンショット画像からOCRで日付を抽出し、Google Calendarに自動でイベントを作成するFlaskアプリケーションです。

## ✨ 主な機能

### 🤖 Slack連携
- **リアルタイム監視**: 指定チャンネルの画像アップロードを自動監視
- **Socket Mode対応**: Slack Events APIを使用したリアルタイム通信
- **設定可能な監視対象**: ワークスペース名・チャンネル名を自由に設定
- **セキュアな認証**: Bot Token・App Tokenによる安全な接続

### 👁️ 高精度OCR機能
- **多言語対応**: 日本語・英語の混在テキストを認識
- **柔軟な日付形式**: 複数の日付パターンに対応
  - `2024年7月20日`
  - `2024/7/20`
  - `2024-7-20`
  - `7月20日`
  - `7/20`
- **カスタムパターン**: 独自の日付フォーマットを追加可能

### 📅 Google Calendar連携
- **自動イベント作成**: 抽出した日付でカレンダーイベントを自動生成
- **柔軟な設定**: デフォルト時刻・期間・タイトルをカスタマイズ
- **複数カレンダー対応**: メインカレンダーや特定カレンダーに対応
- **OAuth2認証**: 安全なGoogle API接続

### ⚙️ 設定管理
- **Web UI設定**: ブラウザから全設定を管理
- **YAML設定ファイル**: 人間が読みやすい設定形式
- **リアルタイム更新**: 設定変更の即座反映
- **バックアップ対応**: 設定のエクスポート・インポート

## 🚀 セットアップ

### 必要要件
- Python 3.7+
- Tesseract OCR
- Slack App (Bot Token・App Token)
- Google Cloud Project (Calendar API有効化)

### インストール

1. **リポジトリのクローン**
```bash
git clone https://github.com/nabsan/NabOwnMonoRepo.git
cd NabOwnMonoRepo/apps/slack2cal
```

2. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

3. **Tesseract OCRのインストール**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

# macOS
brew install tesseract tesseract-lang

# Windows
# https://github.com/UB-Mannheim/tesseract/wiki からダウンロード
```

4. **Slack Appの作成**
- [Slack API](https://api.slack.com/apps)でアプリを作成
- Bot Token Scopes: `files:read`, `channels:read`, `chat:write`
- Socket Mode を有効化してApp Tokenを取得

5. **Google Calendar APIの設定**
- [Google Cloud Console](https://console.cloud.google.com)でプロジェクト作成
- Calendar APIを有効化
- 認証情報（OAuth 2.0）を作成
- `config/google_credentials.json`に配置

6. **設定ファイルの編集**
```bash
# config/settings.yamlを編集
slack:
  workspace_name: "あなたのワークスペース名"
  channel_name: "監視するチャンネル名"
  bot_token: "xoxb-your-bot-token"
  app_token: "xapp-your-app-token"
```

7. **アプリケーションの起動**
```bash
python app.py
```

8. **ブラウザでアクセス**
```
http://localhost:5002
```

## 📖 使用方法

### 初期設定

1. **設定ページにアクセス**: `http://localhost:5002/config`
2. **Slack設定**: ワークスペース名、チャンネル名、各種トークンを入力
3. **Google Calendar設定**: カレンダーIDと認証情報を設定
4. **OCR設定**: 言語と日付パターンを設定
5. **設定保存**: 💾ボタンで設定を保存

### 接続テスト

1. **ダッシュボードにアクセス**: `http://localhost:5002`
2. **Slack接続テスト**: 🤖 Slack連携の「テスト」ボタン
3. **Google Calendar接続テスト**: 📅 Google Calendarの「テスト」ボタン
4. **OCR機能テスト**: 👁️ OCR機能の「テスト」ボタンで画像アップロード

### 監視開始

1. **監視開始**: 🔄 監視状態の「監視開始」ボタン
2. **Slackでテスト**: 指定チャンネルに日付入り画像をアップロード
3. **結果確認**: Google Calendarにイベントが自動作成されることを確認

### OCRテスト機能

- 日付が含まれた画像をアップロードしてOCR精度を確認
- 抽出されたテキストと検出された日付を表示
- 設定調整の参考として活用

## 🔧 設定詳細

### Slack設定
```yaml
slack:
  workspace_name: "myown"          # ワークスペース名
  channel_name: "calendar"        # 監視チャンネル
  bot_token: "xoxb-..."           # Bot User OAuth Token
  app_token: "xapp-..."           # App-Level Token (Socket Mode用)
```

### Google Calendar設定
```yaml
google_calendar:
  calendar_id: "primary"                        # カレンダーID
  credentials_file: "config/google_credentials.json"  # 認証情報ファイル
  token_file: "config/google_token.json"              # トークンファイル
```

### OCR設定
```yaml
ocr:
  language: "jpn+eng"              # 認識言語
  date_patterns:                   # 日付パターン
    - "%Y年%m月%d日"
    - "%Y/%m/%d"
    - "%Y-%m-%d"
    - "%m月%d日"
    - "%m/%d"
```

### イベント設定
```yaml
event:
  default_title: "スケジュール"      # デフォルトタイトル
  default_duration_hours: 1        # デフォルト期間（時間）
  default_time: "09:00"           # デフォルト開始時刻
```

## 🎯 動作フロー

1. **画像アップロード**: Slackの指定チャンネルに画像がアップロード
2. **リアルタイム検知**: Socket Modeでイベントを即座に受信
3. **画像ダウンロード**: Slack APIから画像を一時ダウンロード
4. **OCR処理**: Tesseractで画像からテキストを抽出
5. **日付抽出**: 正規表現で日付パターンをマッチング
6. **カレンダー作成**: Google Calendar APIでイベントを作成
7. **ログ記録**: 処理結果をログに記録
8. **クリーンアップ**: 一時ファイルを削除

## 📁 ディレクトリ構成

```
slack2cal/
├── app.py                  # Flaskアプリケーション
├── requirements.txt        # 依存関係
├── README.md              # このファイル
├── config/
│   ├── settings.yaml      # 設定ファイル
│   ├── google_credentials.json  # Google API認証情報（要作成）
│   └── google_token.json  # Google APIトークン（自動生成）
├── templates/
│   ├── index.html         # ダッシュボード
│   └── config.html        # 設定ページ
├── static/
│   ├── css/
│   │   └── style.css      # スタイルシート
│   └── js/
│       ├── app.js         # ダッシュボードJS
│       └── config.js      # 設定ページJS
├── logs/                  # ログファイル
└── temp/                  # 一時ファイル
```

## 🐛 トラブルシューティング

### Slack接続エラー
1. Bot Tokenが正しいか確認
2. 必要なスコープが設定されているか確認
3. アプリがワークスペースにインストールされているか確認

### Google Calendar接続エラー
1. Google Cloud ProjectでCalendar APIが有効化されているか確認
2. 認証情報ファイルが正しい場所にあるか確認
3. OAuth同意画面の設定を確認

### OCRが機能しない
1. Tesseractが正しくインストールされているか確認
2. 日本語言語パックがインストールされているか確認
3. 画像の解像度・品質を確認

### 日付が検出されない
1. OCR設定の言語が適切か確認
2. 日付パターンが画像内の形式と一致しているか確認
3. 画像のテキストが鮮明か確認

## 🔒 セキュリティ

- **トークン管理**: 設定ファイルでの安全な認証情報管理
- **一時ファイル**: 処理後の自動削除でプライバシー保護
- **HTTPS通信**: Slack・Google APIとの暗号化通信
- **最小権限**: 必要最小限のAPIスコープのみ使用

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビュート

プルリクエストやイシューの報告を歓迎します！

## 📞 サポート

問題が発生した場合は、GitHubのIssuesページでご報告ください。

---

**slack2cal** - Slackの画像から、カレンダーへ。自動化の力で効率的なスケジュール管理を。