from flask import Flask, render_template, request, jsonify, send_file
import markdown
import json
import os
import re
import html
from datetime import datetime
from werkzeug.utils import secure_filename
from io import BytesIO

# Try to import reportlab, handle gracefully if not available
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import platform
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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

def register_japanese_font():
    """Register Japanese font for PDF generation"""
    try:
        # Check what fonts are available in the system
        system = platform.system()
        print(f"DEBUG: Operating system: {system}")
        
        # For WSL, first try Windows fonts directly
        windows_fonts = [
            "/mnt/c/Windows/Fonts/meiryo.ttc",
            "/mnt/c/Windows/Fonts/msgothic.ttc",
            "/mnt/c/Windows/Fonts/msmincho.ttc",
            "/mnt/c/Windows/Fonts/yugothm.ttc",
            "/mnt/c/Windows/Fonts/BIZ-UDGothicR.ttc"
        ]
        
        # Try Windows fonts first (best for Japanese)
        for font_path in windows_fonts:
            if os.path.exists(font_path):
                try:
                    print(f"DEBUG: Trying to register Windows font: {font_path}")
                    # Try with subfontIndex for .ttc files
                    pdfmetrics.registerFont(TTFont('JapaneseFont', font_path, subfontIndex=0))
                    print(f"DEBUG: Successfully registered Windows font: {font_path}")
                    return 'JapaneseFont'
                except Exception as font_error:
                    print(f"DEBUG: Failed to register {font_path}: {font_error}")
                    # Try without subfontIndex
                    try:
                        pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                        print(f"DEBUG: Successfully registered Windows font (no subfont): {font_path}")
                        return 'JapaneseFont'
                    except Exception as font_error2:
                        print(f"DEBUG: Also failed without subfont: {font_error2}")
                        continue
        
        # If Windows fonts fail, try system-specific fonts
        if system == "Windows":
            possible_fonts = [
                "C:/Windows/Fonts/meiryo.ttc",
                "C:/Windows/Fonts/msgothic.ttc"
            ]
        elif system == "Darwin":  # macOS
            possible_fonts = [
                "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc"
            ]
        else:  # Linux
            possible_fonts = [
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
        
        for font_path in possible_fonts:
            if os.path.exists(font_path):
                try:
                    print(f"DEBUG: Trying to register system font: {font_path}")
                    pdfmetrics.registerFont(TTFont('JapaneseFont', font_path))
                    print(f"DEBUG: Successfully registered system font: {font_path}")
                    return 'JapaneseFont'
                except Exception as font_error:
                    print(f"DEBUG: Failed to register {font_path}: {font_error}")
                    continue
        
        # Last resort: use built-in fonts
        print("DEBUG: No Japanese font found, using built-in fonts")
        return 'Helvetica'
            
    except Exception as e:
        print(f"WARNING: Error in font registration: {e}")
        return 'Helvetica'

@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    """Export slides to PDF"""
    if not REPORTLAB_AVAILABLE:
        return jsonify({'error': 'PDF export not available. Please install reportlab: pip install reportlab'}), 500
    
    try:
        data = request.get_json()
        slides = data.get('slides', [])
        
        if not slides:
            return jsonify({'error': 'No slides to export'}), 400
        
        # Register Japanese font
        font_name = register_japanese_font()
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
        
        # Get styles with Japanese font
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=24,
            spaceAfter=30,
            textColor='#2d3748'
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=18,
            spaceAfter=20,
            textColor='#4a5568'
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            spaceAfter=12,
            leading=18
        )
        
        # Build PDF content
        story = []
        
        for i, slide in enumerate(slides):
            content = slide.get('content', '')
            timing = slide.get('timing', 60)
            
            # Add slide number and timing info
            slide_header = f"スライド {i+1} (時間: {timing}秒)"
            safe_header = html.escape(slide_header)
            print(f"DEBUG: Slide header: '{slide_header}' -> '{safe_header}'")
            story.append(Paragraph(safe_header, title_style))
            story.append(Spacer(1, 20))
            
            # Process markdown content line by line
            lines = content.split('\n')  # Use regular newline, not escaped
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                elif line.startswith('# '):
                    # H1
                    text = line[2:].strip()
                    # Properly escape and encode text for PDF
                    safe_text = html.escape(text)
                    print(f"DEBUG: H1 text: '{text}' -> '{safe_text}'")
                    story.append(Paragraph(safe_text, title_style))
                elif line.startswith('## '):
                    # H2
                    text = line[3:].strip()
                    safe_text = html.escape(text)
                    print(f"DEBUG: H2 text: '{text}' -> '{safe_text}'")
                    story.append(Paragraph(safe_text, heading_style))
                elif line.startswith('### '):
                    # H3
                    text = line[4:].strip()
                    safe_text = html.escape(text)
                    print(f"DEBUG: H3 text: '{text}' -> '{safe_text}'")
                    story.append(Paragraph(safe_text, heading_style))
                elif line.startswith('- ') or line.startswith('* '):
                    # List item
                    text = '• ' + line[2:].strip()
                    safe_text = html.escape(text)
                    print(f"DEBUG: List text: '{text}' -> '{safe_text}'")
                    story.append(Paragraph(safe_text, normal_style))
                elif line.startswith('**') and line.endswith('**'):
                    # Bold text
                    inner_text = line[2:-2]
                    safe_text = f"<b>{html.escape(inner_text)}</b>"
                    print(f"DEBUG: Bold text: '{inner_text}' -> '{safe_text}'")
                    story.append(Paragraph(safe_text, normal_style))
                elif not line.startswith('<!--'):
                    # Regular paragraph
                    safe_text = html.escape(line)
                    print(f"DEBUG: Normal text: '{line}' -> '{safe_text}'")
                    story.append(Paragraph(safe_text, normal_style))
            
            # Add page break except for last slide
            if i < len(slides) - 1:
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name='slides.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"DEBUG: Error exporting PDF: {str(e)}")
        return jsonify({'error': f'PDF export failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)