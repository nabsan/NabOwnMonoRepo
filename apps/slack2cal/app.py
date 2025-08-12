from flask import Flask, render_template, request, jsonify, redirect, url_for
import yaml
import os
import logging
import re
from datetime import datetime, timedelta
from dateutil import parser
import requests
from PIL import Image
import tempfile
import schedule
import time
import threading

# Try to import optional dependencies
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from slack_sdk import WebClient
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk.socket_mode.request import SocketModeRequest
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/slack2cal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_file='config/settings.yaml'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Config file {self.config_file} not found, using defaults")
                return self.get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.get_default_config()
    
    def save_config(self):
        """Save configuration to YAML file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get_default_config(self):
        """Return default configuration"""
        return {
            'slack': {
                'workspace_name': 'myown',
                'channel_name': 'calendar',
                'bot_token': '',
                'app_token': ''
            },
            'google_calendar': {
                'calendar_id': 'primary',
                'credentials_file': 'config/google_credentials.json',
                'token_file': 'config/google_token.json'
            },
            'ocr': {
                'language': 'jpn+eng',
                'date_patterns': ['%Y年%m月%d日', '%Y/%m/%d', '%Y-%m-%d', '%m月%d日', '%m/%d']
            },
            'app': {
                'port': 5002,
                'debug': True,
                'log_level': 'INFO',
                'image_download_timeout': 30,
                'temp_folder': 'temp'
            },
            'event': {
                'default_title': 'スケジュール',
                'default_duration_hours': 1,
                'default_time': '09:00'
            }
        }
    
    def get(self, key_path, default=None):
        """Get configuration value using dot notation (e.g., 'slack.workspace_name')"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value

class OCRProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        self.temp_folder = self.config.get('app.temp_folder', 'temp')
        os.makedirs(self.temp_folder, exist_ok=True)
    
    def download_image(self, image_url, headers=None):
        """Download image from URL"""
        try:
            timeout = self.config.get('app.image_download_timeout', 30)
            response = requests.get(image_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png', dir=self.temp_folder) as temp_file:
                temp_file.write(response.content)
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using OCR"""
        if not TESSERACT_AVAILABLE:
            raise Exception("pytesseract not available. Please install: pip install pytesseract")
        
        try:
            # Check if image file exists
            if not os.path.exists(image_path):
                raise Exception(f"Image file not found: {image_path}")
            
            # Open and process image
            image = Image.open(image_path)
            language = self.config.get('ocr.language', 'jpn+eng')
            
            # Check if tesseract executable is available
            try:
                text = pytesseract.image_to_string(image, lang=language)
                logger.info(f"Extracted OCR text: {text[:100] if text else 'No text found'}...")
                return text.strip() if text else ""
            except pytesseract.TesseractNotFoundError:
                raise Exception("Tesseract OCR not found. Please install tesseract-ocr: sudo apt-get install tesseract-ocr tesseract-ocr-jpn")
            except pytesseract.TesseractError as e:
                raise Exception(f"Tesseract OCR error: {e}")
                
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            raise
    
    def extract_dates_from_text(self, text):
        """Extract dates from OCR text"""
        dates = []
        logger.info(f"Extracting dates from text: {repr(text[:200])}...")  # 最初の200文字をログ出力
        
        # Windowsタスクバーや様々な日本語・英語日付パターン
        date_regexes = [
            # Windows taskbar style: yyyy/mm/dd above time
            r'(\d{4})/(\d{1,2})/(\d{1,2})\s*[\n\r]*\s*\d{1,2}:\d{2}',  # 2024/7/20\n13:21
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s*[\n\r]*\s*\d{1,2}:\d{2}',  # 2024-7-20\n13:21
            
            # Standard date formats
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # 2024年7月20日
            r'(\d{4})/(\d{1,2})/(\d{1,2})',      # 2024/7/20
            r'(\d{4})-(\d{1,2})-(\d{1,2})',      # 2024-7-20
            r'(\d{1,2})月(\d{1,2})日',           # 7月20日
            r'(\d{1,2})/(\d{1,2})',              # 7/20
            
            # 令和年表記
            r'令和(\d{1,2})年(\d{1,2})月(\d{1,2})日',  # 令和6年7月20日
            r'令和(\d{1,2})年(\d{1,2})月(\d{1,2})',    # 令和6年7月20
            
            # 時刻付き
            r'(\d{4})/(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})',      # 2024/7/20 13:21
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2}):(\d{2})',      # 2024-7-20 13:21
            r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})',           # 7月20日 13:21
            
            # AM/PM表記
            r'(\d{4})/(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})\s*(AM|PM)',  # 2024/7/20 1:30 PM
            r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})\s*(AM|PM)',       # 7月20日 11:30PM
            
            # スペース含む
            r'(\d{1,2})\s*月\s*(\d{1,2})\s*日',   # 7 月 20 日 (スペース含む)
            r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})',  # 2024 / 7 / 20
        ]
        
        for i, regex in enumerate(date_regexes):
            matches = re.findall(regex, text)
            if matches:
                logger.info(f"Pattern {i+1} ({regex}) found matches: {matches}")
            
            for match in matches:
                try:
                    # 令和年の処理
                    if "令和" in regex:
                        if len(match) == 3:  # 令和年, 月, 日
                            reiwa_year, month, day = match
                            # 令和年を西暦に変換（令和1年=2019年）
                            year = int(reiwa_year) + 2018
                            date_obj = datetime(year, int(month), int(day))
                        else:
                            continue
                    
                    # 時刻付きパターンの処理
                    elif len(match) >= 5:  # Year, month, day, hour, minute [, AM/PM]
                        year, month, day = match[0], match[1], match[2]
                        hour, minute = int(match[3]), int(match[4])
                        
                        # AM/PM処理
                        if len(match) == 6 and match[5] in ['AM', 'PM']:
                            if match[5] == 'PM' and hour != 12:
                                hour += 12
                            elif match[5] == 'AM' and hour == 12:
                                hour = 0
                        
                        date_obj = datetime(int(year), int(month), int(day), hour, minute)
                    
                    # 標準的な日付パターン
                    elif len(match) == 3:  # Year, month, day
                        year, month, day = match
                        # 2桁年の場合は2000年代として扱う
                        if len(year) == 2:
                            year = "20" + year
                        date_obj = datetime(int(year), int(month), int(day))
                    
                    elif len(match) == 2:  # Month, day (use current year)
                        month, day = match
                        current_year = datetime.now().year
                        date_obj = datetime(current_year, int(month), int(day))
                    else:
                        continue
                    
                    dates.append(date_obj)
                    logger.info(f"Found date: {date_obj.strftime('%Y-%m-%d %H:%M')}")
                except ValueError as e:
                    logger.warning(f"Invalid date found: {match} - {e}")
                    continue
        
        return dates
    
    def cleanup_temp_file(self, file_path):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Error cleaning up temp file {file_path}: {e}")

class GoogleCalendarManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/calendar']
    
    def authenticate(self):
        """Authenticate with Google Calendar API"""
        if not GOOGLE_API_AVAILABLE:
            raise Exception("Google API libraries not available. Please install google-api-python-client")
        
        creds = None
        token_file = self.config.get('google_calendar.token_file')
        credentials_file = self.config.get('google_calendar.credentials_file')
        
        # Check if credentials file path is valid
        if not credentials_file:
            raise Exception("Google Calendar credentials file path not configured")
        
        # デフォルトのtoken_fileパスを設定（設定されていない場合）
        if not token_file:
            token_file = 'config/google_token.json'
            self.config.set('google_calendar.token_file', token_file)
            logger.info(f"Token file path not configured, using default: {token_file}")
        
        # Load existing token
        if token_file and os.path.exists(token_file):
            try:
                creds = Credentials.from_authorized_user_file(token_file, self.scopes)
                logger.info(f"Loaded existing credentials from {token_file}")
            except Exception as e:
                logger.warning(f"Error loading existing token: {e}")
                creds = None
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.warning(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(credentials_file):
                    raise Exception(f"Google credentials file not found: {credentials_file}")
                
                logger.info("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)
                logger.info("OAuth flow completed successfully")
            
            # Save credentials
            try:
                os.makedirs(os.path.dirname(token_file), exist_ok=True)
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Saved credentials to {token_file}")
            except Exception as e:
                logger.error(f"Error saving credentials: {e}")
                # Continue without saving - authentication still works for this session
        
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar authentication successful")
        return True
    
    def create_event(self, date, title=None, description=None):
        """Create calendar event"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            if not title:
                title = self.config.get('event.default_title', 'スケジュール')
            
            default_time = self.config.get('event.default_time', '09:00')
            duration_hours = self.config.get('event.default_duration_hours', 1)
            
            # Parse default time
            hour, minute = map(int, default_time.split(':'))
            start_datetime = date.replace(hour=hour, minute=minute)
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            
            event = {
                'summary': title,
                'description': description or f'Slack2Calで自動作成されたイベント',
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
            }
            
            calendar_id = self.config.get('google_calendar.calendar_id', 'primary')
            result = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            
            logger.info(f"Event created: {result.get('htmlLink')}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None

class SlackManager:
    def __init__(self, config_manager, ocr_processor, calendar_manager):
        self.config = config_manager
        self.ocr = ocr_processor
        self.calendar = calendar_manager
        self.client = None
        self.socket_client = None
    
    def initialize(self):
        """Initialize Slack client"""
        if not SLACK_SDK_AVAILABLE:
            raise Exception("Slack SDK not available. Please install: pip install slack-sdk")
        
        bot_token = self.config.get('slack.bot_token')
        app_token = self.config.get('slack.app_token')
        
        if not bot_token:
            raise Exception("Slack bot token not configured")
        
        self.client = WebClient(token=bot_token)
        
        if app_token:
            self.socket_client = SocketModeClient(
                app_token=app_token,
                web_client=self.client
            )
            self.socket_client.socket_mode_request_listeners.append(self.handle_socket_mode_request)
        
        logger.info("Slack client initialized")
        return True
    
    def handle_socket_mode_request(self, client, req):
        """Handle Socket Mode requests from Slack"""
        logger.info(f"Received Socket Mode request: type={req.type}")
        
        if req.type == "events_api":
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Process the event
            event = req.payload.get("event", {})
            logger.info(f"Received event: type={event.get('type')}, channel={event.get('channel')}")
            
            if event.get("type") == "message":
                self.process_message_event(event)
            elif event.get("type") == "file_shared":
                logger.info("File shared event detected")
                self.process_file_event(event)
    
    def process_message_event(self, event):
        """Process message event from Slack"""
        try:
            channel = event.get("channel")
            channel_name = self.config.get('slack.channel_name', 'calendar')
            logger.info(f"Processing message event in channel {channel}, target: {channel_name}")
            
            # Check if message is from the configured channel
            if not self.is_target_channel(channel, channel_name):
                logger.info(f"Message not from target channel, skipping")
                return
            
            # Check if message has file attachments
            files = event.get("files", [])
            logger.info(f"Found {len(files)} files in message")
            for file_info in files:
                if file_info.get("mimetype", "").startswith("image/"):
                    logger.info(f"Processing image file: {file_info.get('name')}")
                    self.process_image_file(file_info)
                    
        except Exception as e:
            logger.error(f"Error processing message event: {e}")
    
    def process_file_event(self, event):
        """Process file_shared event from Slack"""
        try:
            file_id = event.get("file_id")
            if file_id:
                logger.info(f"Processing shared file: {file_id}")
                # Get file info from Slack API
                result = self.client.files_info(file=file_id)
                file_info = result["file"]
                
                if file_info.get("mimetype", "").startswith("image/"):
                    logger.info(f"Processing shared image file: {file_info.get('name')}")
                    self.process_image_file(file_info)
                    
        except Exception as e:
            logger.error(f"Error processing file event: {e}")
    
    def is_target_channel(self, channel_id, target_channel_name):
        """Check if channel matches target channel"""
        try:
            result = self.client.conversations_info(channel=channel_id)
            channel_info = result["channel"]
            return channel_info["name"] == target_channel_name
        except Exception as e:
            logger.error(f"Error checking channel info: {e}")
            return False
    
    def process_image_file(self, file_info):
        """Process image file from Slack"""
        try:
            image_url = file_info.get("url_private_download")
            if not image_url:
                logger.warning("No download URL found for image")
                return
            
            # Download image
            headers = {"Authorization": f"Bearer {self.config.get('slack.bot_token')}"}
            temp_image_path = self.ocr.download_image(image_url, headers)
            
            if not temp_image_path:
                logger.error("Failed to download image")
                return
            
            try:
                # Extract text from image
                text = self.ocr.extract_text_from_image(temp_image_path)
                if not text:
                    logger.warning("No text extracted from image")
                    return
                
                # Extract dates from text
                dates = self.ocr.extract_dates_from_text(text)
                if not dates:
                    logger.warning("No dates found in extracted text")
                    return
                
                # Create calendar events for each date
                for date in dates:
                    result = self.calendar.create_event(date)
                    if result:
                        logger.info(f"Created calendar event for {date.strftime('%Y-%m-%d')}")
                    else:
                        logger.error(f"Failed to create calendar event for {date.strftime('%Y-%m-%d')}")
                        
            finally:
                # Clean up temporary file
                self.ocr.cleanup_temp_file(temp_image_path)
                
        except Exception as e:
            logger.error(f"Error processing image file: {e}")
    
    def start_socket_mode(self):
        """Start Socket Mode connection"""
        try:
            if not self.socket_client:
                logger.error("Socket Mode client not initialized")
                return False
                
            logger.info("Starting Socket Mode connection...")
            self.socket_client.connect()
            logger.info("Slack Socket Mode started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Socket Mode: {e}")
            return False

# Initialize components
config_manager = ConfigManager()
ocr_processor = OCRProcessor(config_manager)
calendar_manager = GoogleCalendarManager(config_manager)
slack_manager = SlackManager(config_manager, ocr_processor, calendar_manager)

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', config=config_manager.config)

@app.route('/config')
def config_page():
    """Configuration page"""
    return render_template('config.html', config=config_manager.config)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API endpoint for configuration management"""
    if request.method == 'GET':
        return jsonify(config_manager.config)
    
    elif request.method == 'POST':
        try:
            new_config = request.get_json()
            config_manager.config.update(new_config)
            success = config_manager.save_config()
            
            if success:
                # Reinitialize global objects with new configuration
                global slack_manager, calendar_manager, ocr_processor
                try:
                    calendar_manager = GoogleCalendarManager(config_manager)
                    ocr_processor = OCRProcessor(config_manager)
                    slack_manager = SlackManager(config_manager, ocr_processor, calendar_manager)
                    logger.info("Global objects reinitialized with new configuration")
                except Exception as e:
                    logger.warning(f"Warning during reinitialization: {e}")
                
                return jsonify({'success': True, 'message': 'Configuration saved successfully'})
            else:
                return jsonify({'success': False, 'error': 'Failed to save configuration'}), 500
                
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-ocr', methods=['POST'])
def test_ocr():
    """Test OCR functionality"""
    temp_path = None
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file type
        if not file.content_type or not file.content_type.startswith('image/'):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload an image file.'}), 400
        
        # Save uploaded file temporarily
        import uuid
        safe_filename = f"ocr_test_{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(ocr_processor.temp_folder, safe_filename)
        file.save(temp_path)
        
        # Extract text and dates
        text = ocr_processor.extract_text_from_image(temp_path)
        dates = ocr_processor.extract_dates_from_text(text) if text else []
        
        return jsonify({
            'success': True,
            'extracted_text': text or "（テキストが検出されませんでした）",
            'found_dates': [date.strftime('%Y-%m-%d') for date in dates]
        })
        
    except Exception as e:
        logger.error(f"Error in OCR test: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {cleanup_error}")

@app.route('/api/test-calendar', methods=['POST'])
def test_calendar():
    """Test Google Calendar connection"""
    try:
        # Check if credentials file exists
        credentials_file = calendar_manager.config.get('google_calendar.credentials_file')
        if not credentials_file:
            return jsonify({'success': False, 'error': 'Google Calendar credentials file path not configured'}), 500
        
        if not os.path.exists(credentials_file):
            return jsonify({'success': False, 'error': f'Credentials file not found: {credentials_file}'}), 500
        
        # Test event creation with sample date
        test_date = datetime(2026, 1, 1, 0, 0)
        result = calendar_manager.create_event(test_date, title="お正月", description="テストイベント")
        
        if result:
            return jsonify({'success': True, 'message': f'Google Calendar test successful. Event created: {result.get("htmlLink", "N/A")}'})
        else:
            return jsonify({'success': False, 'error': 'Failed to create test event'}), 500
        
    except Exception as e:
        logger.error(f"Error testing calendar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-slack', methods=['POST'])
def test_slack():
    """Test Slack connection"""
    try:
        result = slack_manager.initialize()
        if result:
            return jsonify({'success': True, 'message': 'Slack connection successful'})
        else:
            return jsonify({'success': False, 'error': 'Connection failed'}), 500
    except Exception as e:
        logger.error(f"Error testing Slack: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/start-monitoring', methods=['POST'])
def start_monitoring():
    """Start Slack monitoring"""
    try:
        # Initialize Slack client
        if not slack_manager.initialize():
            return jsonify({'success': False, 'error': 'Failed to initialize Slack client'}), 500
        
        # Start Socket Mode
        if not slack_manager.start_socket_mode():
            return jsonify({'success': False, 'error': 'Failed to start Socket Mode connection'}), 500
            
        return jsonify({'success': True, 'message': 'Slack monitoring started successfully'})
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    
    port = config_manager.get('app.port', 5002)
    debug = config_manager.get('app.debug', True)
    
    app.run(debug=debug, host='0.0.0.0', port=port)