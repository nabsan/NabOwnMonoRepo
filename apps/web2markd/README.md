# web2markd

🌐 **WebサイトをMarkdownに変換するWebアプリ**

web2markdは、Webサイトをクロールしてコンテンツを抽出し、LLM入力用のMarkdownファイルとして効率的に保存できるFlaskアプリケーションです。

## ✨ 主な機能

### 🕷️ Webクロール機能
- **URL自動取得**: HTTPSプロトコル自動補完
- **リアルタイム処理**: 非同期でコンテンツを取得
- **エラーハンドリング**: 接続エラーやタイムアウトに対応

### 📋 高度なフィルタリング
- **自動広告除去**: 広告、ナビゲーション、サイドバーを自動検出・除去
- **CSS選択子フィルター**: 特定の要素を除去または保持
- **HTMLタグフィルター**: 不要なタグ（script、style、iframe等）を除去
- **Readabilityアルゴリズム**: メインコンテンツを自動抽出

### 📝 Markdown変換
- **高品質変換**: html2textライブラリによる正確な変換
- **構造保持**: 見出し、リスト、リンク、強調表示を保持
- **UTF-8対応**: 日本語コンテンツを適切に処理
- **自動整形**: 不要な改行を削除し、読みやすい形式に整形

### 💾 ファイル管理
- **自動ファイル名生成**: ドメイン名+タイムスタンプ
- **カスタムファイル名**: 任意のファイル名を指定可能
- **一覧表示**: 保存済みファイルの一覧とメタデータ表示
- **ダウンロード機能**: ワンクリックでファイルダウンロード

## 🚀 セットアップ

### 必要要件
- Python 3.7+
- Flask
- BeautifulSoup4
- html2text
- readability-lxml
- requests

### インストール

1. **リポジトリのクローン**
```bash
git clone https://github.com/nabsan/NabOwnMonoRepo.git
cd NabOwnMonoRepo/apps/web2markd
```

2. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

3. **アプリケーションの起動**
```bash
python app.py
```

4. **ブラウザでアクセス**
```
http://localhost:5001
```

## 📖 使用方法

### 基本的な使い方

1. **URL入力**: 変換したいWebサイトのURLを入力
2. **フィルター設定**: 必要に応じてコンテンツフィルターを設定
3. **クロール実行**: 🕷️ クロール開始ボタンをクリック
4. **プレビュー確認**: 抽出されたコンテンツをプレビューで確認
5. **ファイル保存**: 💾 保存ボタンでMarkdownファイルとして保存

### フィルター設定詳細

#### 📋 自動フィルター
- **広告・ナビゲーション除去**: 一般的な広告やナビゲーション要素を自動除去

#### 🎯 カスタムフィルター
- **除去するCSS選択子**: 特定のクラスやIDの要素を除去
  ```
  .advertisement, .social-share, #sidebar
  ```
- **保持するCSS選択子**: 指定した要素のみを保持
  ```
  article, .content, main
  ```
- **除去するHTMLタグ**: 特定のHTMLタグを除去
  ```
  script, style, iframe, nav
  ```

### 使用例

#### ニュースサイトの記事抽出
```
URL: https://example-news.com/article/123
除去選択子: .sidebar, .related-articles, .advertisement
保持選択子: article, .article-content
除去タグ: script, style, aside
```

#### ブログ記事の抽出
```
URL: https://blog.example.com/post/my-article
除去選択子: .author-bio, .social-share, .comments
保持選択子: .post-content, .post-title
除去タグ: script, iframe
```

#### 技術文書の抽出
```
URL: https://docs.example.com/guide/setup
除去選択子: .navigation, .toc, .edit-page
保持選択子: .content, main
除去タグ: script, style
```

## 🔧 技術仕様

### バックエンド
- **Flask**: 軽量なWebフレームワーク
- **BeautifulSoup4**: HTMLパースと操作
- **html2text**: HTML→Markdown変換
- **readability-lxml**: メインコンテンツ自動抽出
- **requests**: HTTP通信

### フロントエンド
- **HTML5**: セマンティックな構造
- **CSS3**: レスポンシブデザインとアニメーション
- **JavaScript**: インタラクティブなUI

### 対応コンテンツ
- **日本語サイト**: UTF-8エンコーディング対応
- **海外サイト**: 多言語対応
- **レスポンシブサイト**: モバイル・デスクトップ両対応

## 📁 ディレクトリ構成

```
web2markd/
├── app.py                  # Flaskアプリケーション
├── requirements.txt        # 依存関係
├── README.md              # このファイル
├── templates/
│   └── index.html         # メインHTMLテンプレート
├── static/
│   ├── css/
│   │   └── style.css      # スタイルシート
│   └── js/
│       └── app.js         # JavaScriptアプリケーション
└── downloads/             # 保存されたMarkdownファイル
```

## 🎯 LLM活用のベストプラクティス

### 効果的なコンテンツ抽出
1. **メインコンテンツのみ抽出**: 不要な要素を除去してノイズを削減
2. **構造化された形式**: 見出しやリストを保持してLLMが理解しやすい形式に
3. **適切なファイル名**: 内容が分かりやすいファイル名を設定

### 推奨フィルター設定
- **技術文書**: `.sidebar, .navigation, .breadcrumb`を除去
- **ニュース記事**: `.advertisement, .related, .comments`を除去
- **ブログ**: `.author-info, .social-share, .sidebar`を除去

## 🐛 トラブルシューティング

### よくある問題

#### コンテンツが取得できない
1. URLが正しいか確認
2. サイトがJavaScriptを多用していないか確認
3. アクセス制限がかかっていないか確認

#### フィルターが効かない
1. CSS選択子の記法が正しいか確認
2. 対象要素が実際に存在するか開発者ツールで確認
3. readabilityアルゴリズムが既に除去している可能性

#### 文字化けが発生
1. サイトのエンコーディングを確認
2. UTF-8以外の場合は自動変換される

## 🔒 セキュリティ

- **安全なURL検証**: 不正なURLからの保護
- **ファイルサイズ制限**: 大容量ファイルの制限
- **サニタイゼーション**: XSSやインジェクション攻撃の防御

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 コントリビュート

プルリクエストやイシューの報告を歓迎します！

## 📞 サポート

問題が発生した場合は、GitHubのIssuesページでご報告ください。

---

**web2markd** - WebコンテンツをLLM入力用に効率的に変換。