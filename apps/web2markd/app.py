from flask import Flask, render_template, request, jsonify, send_file
import re
import os
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
import time

# Try to import optional dependencies
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Disable SSL warnings
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False

try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Create downloads directory if it doesn't exist
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

class WebCrawler:
    def __init__(self):
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
        else:
            self.session = None
    
    def fetch_url(self, url, timeout=30):
        """Fetch content from URL"""
        if not REQUESTS_AVAILABLE:
            raise Exception("requests library not available. Please install: pip install requests")
        
        try:
            print(f"DEBUG: Fetching URL: {url}")
            
            # Configure session for better compatibility
            self.session.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # Try with SSL verification disabled for older sites
            response = self.session.get(url, timeout=timeout, verify=False, allow_redirects=True)
            response.raise_for_status()
            
            # Handle encoding properly
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            
            print(f"DEBUG: Successfully fetched {len(response.text)} characters")
            print(f"DEBUG: Response encoding: {response.encoding}")
            print(f"DEBUG: Response status: {response.status_code}")
            
            # Check if this is a frameset page and extract main content
            if '<frameset' in response.text.lower() or '<frame' in response.text.lower():
                print("DEBUG: Detected frameset page, trying to extract main content")
                return self.handle_frameset(response.text, url)
            
            return response.text
            
        except requests.exceptions.SSLError as e:
            print(f"DEBUG: SSL Error, trying without SSL verification: {e}")
            try:
                response = self.session.get(url, timeout=timeout, verify=False, allow_redirects=True)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                print(f"DEBUG: Successfully fetched with SSL verification disabled")
                return response.text
            except Exception as e2:
                print(f"DEBUG: Failed even without SSL verification: {e2}")
                raise e2
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request error: {e}")
            raise e
        except Exception as e:
            print(f"DEBUG: Unexpected error fetching URL: {e}")
            raise e
    
    def handle_frameset(self, frameset_html, base_url):
        """Handle frameset pages by extracting content from main frame"""
        try:
            if not BS4_AVAILABLE:
                return frameset_html
            
            soup = BeautifulSoup(frameset_html, 'html.parser')
            frames = soup.find_all('frame')
            
            main_content = ""
            
            for frame in frames:
                src = frame.get('src', '')
                if src:
                    # Try to fetch content from frame
                    frame_url = urljoin(base_url, src)
                    print(f"DEBUG: Fetching frame content from: {frame_url}")
                    
                    try:
                        frame_response = self.session.get(frame_url, timeout=30, verify=False)
                        frame_response.raise_for_status()
                        
                        # Handle encoding for frame content
                        if frame_response.encoding is None or frame_response.encoding == 'ISO-8859-1':
                            frame_response.encoding = frame_response.apparent_encoding or 'shift_jis'
                        
                        frame_content = frame_response.text
                        print(f"DEBUG: Fetched frame content: {len(frame_content)} characters")
                        
                        # Accumulate content from all frames
                        main_content += f"\n\n<!-- Frame: {src} -->\n" + frame_content
                        
                    except Exception as e:
                        print(f"DEBUG: Error fetching frame {src}: {e}")
                        continue
            
            return main_content if main_content else frameset_html
            
        except Exception as e:
            print(f"DEBUG: Error handling frameset: {e}")
            return frameset_html
    
    def extract_readable_content(self, html_content, filter_options=None):
        """Extract main content using readability and custom filters"""
        try:
            title = "Web Content"
            readable_html = html_content
            
            # Use readability if available
            if READABILITY_AVAILABLE:
                doc = Document(html_content)
                title = doc.title()
                readable_html = doc.summary()
                print(f"DEBUG: Extracted title: {title}")
                print(f"DEBUG: Readable content length: {len(readable_html)}")
            else:
                print("DEBUG: Readability not available, using raw HTML")
            
            # Parse with BeautifulSoup for further filtering if available
            if BS4_AVAILABLE:
                soup = BeautifulSoup(readable_html, 'html.parser')
                
                # Apply custom filters if provided
                if filter_options:
                    soup = self.apply_content_filters(soup, filter_options)
                
                return title, str(soup)
            else:
                print("DEBUG: BeautifulSoup not available, using raw HTML")
                return title, readable_html
            
        except Exception as e:
            print(f"DEBUG: Error in content extraction: {e}")
            raise e
    
    def apply_content_filters(self, soup, filter_options):
        """Apply custom content filtering"""
        if not BS4_AVAILABLE:
            return soup
            
        try:
            # Remove elements by CSS selector
            if filter_options.get('remove_selectors'):
                for selector in filter_options['remove_selectors']:
                    for element in soup.select(selector):
                        element.decompose()
            
            # Remove elements by tag name
            if filter_options.get('remove_tags'):
                for tag in filter_options['remove_tags']:
                    for element in soup.find_all(tag):
                        element.decompose()
            
            # Keep only specific selectors
            if filter_options.get('keep_selectors'):
                new_soup = BeautifulSoup('', 'html.parser')
                for selector in filter_options['keep_selectors']:
                    for element in soup.select(selector):
                        new_soup.append(element.extract())
                soup = new_soup
            
            # Remove advertisements and navigation
            common_ad_selectors = [
                '.ad', '.ads', '.advertisement', '.banner',
                '.sidebar', '.navigation', '.nav', '.menu',
                '.footer', '.header', '.social', '.share',
                '.related', '.comments', '.comment-form'
            ]
            
            if filter_options.get('remove_ads', True):
                for selector in common_ad_selectors:
                    for element in soup.select(selector):
                        element.decompose()
            
            return soup
            
        except Exception as e:
            print(f"DEBUG: Error in content filtering: {e}")
            return soup
    
    def html_to_markdown(self, html_content, title=""):
        """Convert HTML to Markdown"""
        try:
            if HTML2TEXT_AVAILABLE:
                # Configure html2text
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.ignore_emphasis = False
                h.body_width = 0  # Don't wrap lines
                h.unicode_snob = True
                h.escape_snob = True
                
                # Convert to markdown
                markdown_content = h.handle(html_content)
            else:
                # Simple HTML to text conversion
                import html
                # Remove HTML tags with simple regex
                markdown_content = re.sub(r'<[^>]+>', '', html_content)
                markdown_content = html.unescape(markdown_content)
                print("DEBUG: html2text not available, using simple text extraction")
            
            # Add title if provided
            if title and title != "Web Content":
                markdown_content = f"# {title}\n\n{markdown_content}"
            
            # Clean up extra newlines
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
            
            print(f"DEBUG: Converted to markdown, length: {len(markdown_content)}")
            return markdown_content
            
        except Exception as e:
            print(f"DEBUG: Error in markdown conversion: {e}")
            raise e
    
    def save_markdown(self, content, filename=None):
        """Save markdown content to file"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"web_content_{timestamp}.md"
            
            # Ensure .md extension
            if not filename.endswith('.md'):
                filename += '.md'
            
            filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"DEBUG: Saved markdown to {filepath}")
            return filepath
            
        except Exception as e:
            print(f"DEBUG: Error saving markdown: {e}")
            raise e

# Initialize crawler
crawler = WebCrawler()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/crawl', methods=['POST'])
def crawl_url():
    """Crawl URL and extract content"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        filter_options = data.get('filter_options', {})
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate and normalize URL
        if not url.startswith(('http://', 'https://')):
            # Try HTTPS first, fallback to HTTP if needed
            url = 'https://' + url
        
        print(f"DEBUG: Normalized URL: {url}")
        
        # Handle special cases for older websites
        if 'coocan.jp' in url or 'geocities' in url or url.startswith('http://'):
            # These sites might not support HTTPS
            if url.startswith('https://') and ('coocan.jp' in url or 'geocities' in url):
                url = url.replace('https://', 'http://')
                print(f"DEBUG: Converted to HTTP for older site: {url}")
        
        print(f"DEBUG: Starting crawl for URL: {url}")
        
        # Check dependencies
        if not REQUESTS_AVAILABLE:
            return jsonify({'error': 'requests library not installed. Please run: pip install requests'}), 500
        
        # Fetch content
        html_content = crawler.fetch_url(url)
        
        # Extract readable content
        title, readable_html = crawler.extract_readable_content(html_content, filter_options)
        
        # Convert to markdown
        markdown_content = crawler.html_to_markdown(readable_html, title)
        
        # Generate preview (first 1000 characters)
        preview = markdown_content[:1000] + "..." if len(markdown_content) > 1000 else markdown_content
        
        return jsonify({
            'success': True,
            'title': title,
            'content': markdown_content,
            'preview': preview,
            'url': url,
            'content_length': len(markdown_content),
            'dependencies': {
                'requests': REQUESTS_AVAILABLE,
                'beautifulsoup4': BS4_AVAILABLE,
                'html2text': HTML2TEXT_AVAILABLE,
                'readability': READABILITY_AVAILABLE
            }
        })
        
    except Exception as e:
        print(f"DEBUG: Error in crawl_url: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to crawl URL: {str(e)}',
            'dependencies': {
                'requests': REQUESTS_AVAILABLE,
                'beautifulsoup4': BS4_AVAILABLE,
                'html2text': HTML2TEXT_AVAILABLE,
                'readability': READABILITY_AVAILABLE
            }
        }), 500

@app.route('/save', methods=['POST'])
def save_content():
    """Save content to markdown file"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        filename = data.get('filename', '')
        
        if not content:
            return jsonify({'error': 'No content to save'}), 400
        
        # Save markdown file
        filepath = crawler.save_markdown(content, filename)
        
        return jsonify({
            'success': True,
            'message': f'Content saved to {os.path.basename(filepath)}',
            'filename': os.path.basename(filepath)
        })
        
    except Exception as e:
        print(f"DEBUG: Error in save_content: {str(e)}")
        return jsonify({'error': f'Failed to save content: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download saved markdown file"""
    try:
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/files')
def list_files():
    """List saved markdown files"""
    try:
        files = []
        download_dir = app.config['DOWNLOAD_FOLDER']
        
        for filename in os.listdir(download_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(download_dir, filename)
                stat = os.stat(filepath)
                files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({'files': files})
        
    except Exception as e:
        print(f"DEBUG: Error listing files: {str(e)}")
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)