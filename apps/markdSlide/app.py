from flask import Flask, render_template, request, jsonify, send_file
import markdown
import json
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def parse_markdown_slides(markdown_text):
    """Parse markdown text into slides with timing information"""
    slides = []
    slide_content = []
    current_timing = 60  # Default 1 minute per slide
    
    lines = markdown_text.split('\n')
    
    for line in lines:
        if line.startswith('---'):
            if slide_content:
                slides.append({
                    'content': '\n'.join(slide_content),
                    'timing': current_timing
                })
                slide_content = []
            current_timing = 60  # Reset to default
        elif line.startswith('<!-- timing:'):
            # Extract timing from comment <!-- timing: 120 -->
            match = re.search(r'timing:\s*(\d+)', line)
            if match:
                current_timing = int(match.group(1))
        else:
            slide_content.append(line)
    
    # Add the last slide
    if slide_content:
        slides.append({
            'content': '\n'.join(slide_content),
            'timing': current_timing
        })
    
    return slides

def get_sample_markdown():
    """Return sample markdown content explaining the app"""
    return """# markdSlide Web UI

## 概要
<!-- timing: 90 -->

markdSlideは、Markdownを使用してプレゼンテーションを作成・表示するWebアプリケーションです。

**主な機能:**
- Markdownでスライドを作成
- 全画面・中間サイズ表示
- タイマー機能（ボーナスタイム付き）
- エフェクトとトランジション
- ファイル保存・読み込み

---

## 使用方法
<!-- timing: 120 -->

### 基本操作
1. 左側のエディターにMarkdownを入力
2. 「プレゼン開始」ボタンでプレゼンモードに切り替え
3. 矢印キーでスライド移動
4. 「F」キーで全画面切り替え

### Markdownの書き方
- `---` でスライドを区切る
- `<!-- timing: 秒数 -->` でスライドの時間を設定
- 通常のMarkdown記法が使用可能

---

## 時間管理機能
<!-- timing: 60 -->

### タイマー機能
- 各スライドに設定された時間でカウントダウン
- 時間が余った場合は「ボーナスタイム」として次のスライドに繰り越し
- 画面右上にタイマーとボーナスタイム表示

### ボーナスタイム
前のスライドで浮いた時間は次のスライドで「+●秒使えます」として表示されます。

---

## ショートカットキー
<!-- timing: 45 -->

- **F**: 全画面表示の切り替え
- **←**: 前のスライドに移動
- **→**: 次のスライドに移動
- **ESC**: プレゼンモードを終了

---

## ファイル機能
<!-- timing: 30 -->

- **保存**: 現在のMarkdownをファイルとして保存
- **読み込み**: 既存のMarkdownファイルを読み込み
- **編集**: エディターでリアルタイム編集が可能

---

## 技術仕様
<!-- timing: 60 -->

- **フレームワーク**: Flask (Python3)
- **フロントエンド**: HTML5, CSS3, JavaScript
- **マークダウン**: Python-Markdown
- **エフェクト**: CSS3 Transitions & Animations
- **音響**: Web Audio API

プレゼンテーションを始めましょう！"""

@app.route('/')
def index():
    """Main page with markdown editor"""
    sample_markdown = get_sample_markdown()
    return render_template('index.html', sample_markdown=sample_markdown)

@app.route('/parse_slides', methods=['POST'])
def parse_slides():
    """Parse markdown into slides"""
    data = request.get_json()
    markdown_text = data.get('markdown', '')
    
    slides = parse_markdown_slides(markdown_text)
    
    # Convert markdown to HTML for each slide
    for slide in slides:
        slide['html'] = markdown.markdown(slide['content'], extensions=['codehilite', 'fenced_code'])
    
    return jsonify({'slides': slides})

@app.route('/save_file', methods=['POST'])
def save_file():
    """Save markdown content to file"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        filename = data.get('filename', 'presentation.md')
        
        print(f"DEBUG: Saving file - filename: {filename}, content length: {len(content)}")
        
        # Secure the filename
        filename = secure_filename(filename)
        if not filename.endswith('.md'):
            filename += '.md'
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"DEBUG: Saving to path: {filepath}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"DEBUG: File saved successfully")
        return jsonify({'success': True, 'message': f'File saved as {filename}'})
    except Exception as e:
        print(f"DEBUG: Error saving file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/load_file', methods=['POST'])
def load_file():
    """Load markdown content from file"""
    try:
        print(f"DEBUG: Load file request received")
        print(f"DEBUG: Request files: {request.files}")
        
        if 'file' not in request.files:
            print(f"DEBUG: No file in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        print(f"DEBUG: File received: {file.filename}")
        
        if file.filename == '':
            print(f"DEBUG: Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.endswith('.md'):
            try:
                content = file.read().decode('utf-8')
                print(f"DEBUG: File content length: {len(content)}")
                return jsonify({'content': content})
            except Exception as e:
                print(f"DEBUG: Error reading file content: {str(e)}")
                return jsonify({'error': f'Error reading file: {str(e)}'}), 500
        
        print(f"DEBUG: Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type. Please upload a .md file'}), 400
    except Exception as e:
        print(f"DEBUG: Unexpected error in load_file: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)