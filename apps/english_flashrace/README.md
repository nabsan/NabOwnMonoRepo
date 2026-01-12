# English Flashrace - 英単語タイムトライアルゲーム

概要
----
English Flashrace は、１秒以内に単語を理解できるかを測るタイムトライアル型の英単語学習ゲームです。
複数ユーザーが参加でき、正答率とタイム記録でランキングを競うことができます。


## 必要な環境

- Python 3.8以上
- pip


## セットアップ手順

1. このディレクトリに移動
   ```bash
   cd /home/nab/develop/NabOwnMonoRepo/apps/english_flashrace
   ```

2. 依存ライブラリをインストール
   ```bash
   pip install -r requirements.txt
   ```

3. 環境設定ファイルを作成（必須）
   .env.sample をコピーして .env を作成し、ユーザー認証情報を設定
   ```bash
   cp .env.sample .env
   ```
   
   .env の内容例:
   ```
   USERS=user:xxx,user1:password1,user2:password2
   SECRET_KEY=change-me-long-random
   SKIP_PENALTY_SECONDS=2.0
   RESULTS_DIR=data
   ```


## 起動方法

1. ディレクトリに移動
   ```bash
   cd /home/nab/develop/NabOwnMonoRepo/apps/english_flashrace
   ```

2. サーバーを起動
   ```bash
   python3 ./app/main.py
   ```

3. ブラウザでアクセス
   ```
   http://localhost:8000
   ```


## 使い方

1. **ログイン**
   - トップページで、.envに設定したユーザー名とパスワードでログイン

2. **リスト選択**
   - 学習したい単語リストを選択

3. **ゲーム実行**
   - 単語が表示されます
   - 「知ってる」または「知らない」ボタンを押してください
   - ボタンを押した時間が計測されます

4. **結果表示**
   - 150問完了後、「finish」ボタンを押すと結果画面に遷移
   - 合計時間、平均時間（秒/問）、正答数が表示されます

5. **ランキング確認**
   - トップページの「ランキング Top 10を見る」で全ユーザーの記録を確認
   - 総合時間が短いほど上位になります


## ポート設定

デフォルトではポート 8000 で起動します。
異なるポートで起動する場合は、app/main.py の最後の行を編集してください。

現在:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

変更例（ポート 8080 を使う場合）:
```python
uvicorn.run(app, host="0.0.0.0", port=8080)
```


## データ保存

- ゲーム結果は `data/` ディレクトリに JSON ファイルとして保存されます
- ユーザー認証情報は `.env` ファイルで管理されます（.gitignore で除外）


## トラブルシューティング

### Q: "{'detail': 'Unauthorized'}" が表示される
**A:** ログインが必要です。/login でログインしてください

### Q: ファイアウォールエラーが出る
**A:** ポート 8000 をファイアウォールで許可してください
```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```


## ゲーム仕様

- **総問数:** 150問
- **計測対象:** 単語表示から回答ボタン押下までの時間
- **結果判定:** 「知ってる」「知らない」どちらを選んでも時間が記録されます
- **ランキング:** 総合時間（秒）が小さい順に Top 10 を表示
