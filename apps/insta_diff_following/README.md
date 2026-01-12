# Instagram Follow Difference Manager

Instagramアカウントのフォロー/フォロワー管理ツール。相互フォローでないユーザーを特定し、アンフォロー処理を行います。

## 機能

- **フォロー分析**: フォロワーとフォロー中のユーザーを比較
- **非相互フォロー検出**: 以下の3パターンを識別
  - 相互フォロー: 両方がフォローしている
  - 一方的フォロー: 自分だけがフォロー（アンフォロー推奨）
  - 一方的フォロワー: 相手だけがフォロー
- **安全なアンフォロー**: DRY_RUN モードとレート制限付き

## セットアップ

### 1. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数を設定

`.env.sample` をコピーして `.env` を作成：

```bash
cp .env.sample .env
```

`.env` ファイルを編集してInstagramの認証情報を入力：

```env
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
DRY_RUN=true
DELAY_BETWEEN_UNFOLLOWS=3
```

## 使い方

### 1. フォロー差分を分析

```bash
python main.py
```

このコマンドが以下を実行します：
- Instagramにログイン
- フォロワーリストを取得
- フォロー中のユーザーリストを取得
- 相互フォロー関係を分析
- `follow_analysis.json` に結果を保存
- 対話的にアンフォロー処理を選択

### 2. レポートを生成

```bash
python report_generator.py
```

タイムスタンプ付きのレポートファイル（`follow_report_*.txt`）を生成します。

### 3. 自動アンフォロー（高度な使用）

```bash
python auto_unfollow.py
```

オプション：
- `--max N`: 最大N件まで処理
- `--no-confirm`: 確認なしに実行（注意！）

例：
```bash
python auto_unfollow.py --max 10          # 最初の10件のみ
python auto_unfollow.py --no-confirm      # 確認スキップ
```

## 安全機能

### DRY_RUN モード
デフォルトで `DRY_RUN=true` に設定されています。実際のアンフォロー処理は実行されず、シミュレーションのみです。

実際に処理するには `.env` で `DRY_RUN=false` に設定してください。

### レート制限
`DELAY_BETWEEN_UNFOLLOWS` でアンフォロー間の遅延を制御（デフォルト3秒）。Instagramの制限を回避するため3秒以上の遅延を推奨します。

## セッション管理

ログイン情報は `session.json` に保存されます。再実行時はこのセッションが使用されるため、毎回パスワード入力は不要です。

セッションを削除して再ログインする場合：
```bash
rm session.json
```

## 出力ファイル

- `follow_analysis.json`: フォロー分析の詳細データ（JSON形式）
- `follow_report_*.txt`: 人間が読みやすいレポート

## 注意事項

⚠️ **重要**: Instagramの利用規約を遵守してください。
- 大量のアンフォロー処理は一時的にアカウントがロックされる可能性があります
- レート制限（`DELAY_BETWEEN_UNFOLLOWS`）を守ってください
- DRY_RUN で十分確認してから実際の処理を行ってください

## トラブルシューティング

### ログイン失敗
- ユーザー名とパスワードが正しいか確認
- 2要素認証が有効な場合は別途対応が必要
- セッションファイルを削除して再試行

### "session.json" エラー
セッションキャッシュが破損している可能性があります：
```bash
rm session.json
```

## DEBUG 出力

実行中に `DEBUG:` で始まるメッセージが表示されます。トラブル時はこれらをご確認ください。

## ライセンス

このツールは個人使用を目的としています。Instagram の利用規約に違反しない範囲でご使用ください。
