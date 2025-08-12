class Slack2CalApp {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.checkSystemStatus();
    }
    
    bindEvents() {
        // Test buttons
        document.getElementById('test-slack')?.addEventListener('click', () => this.testSlack());
        document.getElementById('test-calendar')?.addEventListener('click', () => this.testCalendar());
        document.getElementById('test-ocr')?.addEventListener('click', () => this.triggerOCRTest());
        document.getElementById('start-monitoring')?.addEventListener('click', () => this.startMonitoring());
        
        // OCR test
        document.getElementById('ocr-file-input')?.addEventListener('change', (e) => this.handleOCRFile(e));
        document.getElementById('upload-drop-zone')?.addEventListener('click', () => {
            document.getElementById('ocr-file-input').click();
        });
        
        // Drag and drop
        this.setupDragAndDrop();
        
        // Log management
        document.getElementById('clear-log')?.addEventListener('click', () => this.clearLog());
    }
    
    setupDragAndDrop() {
        const dropZone = document.getElementById('upload-drop-zone');
        if (!dropZone) return;
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.processOCRFile(files[0]);
            }
        });
    }
    
    async testSlack() {
        const button = document.getElementById('test-slack');
        const status = document.getElementById('slack-status');
        
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch('/api/test-slack', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus('slack-status', 'connected', data.message);
                this.showMessage('Slack接続テスト成功', 'success');
                this.addLogEntry('success', 'Slack接続テスト成功');
            } else {
                this.updateStatus('slack-status', 'error', data.error);
                this.showMessage(`Slack接続エラー: ${data.error}`, 'error');
                this.addLogEntry('error', `Slack接続エラー: ${data.error}`);
            }
            
        } catch (error) {
            this.updateStatus('slack-status', 'error', 'テスト失敗');
            this.showMessage(`Slack接続テストエラー: ${error.message}`, 'error');
            this.addLogEntry('error', `Slack接続テストエラー: ${error.message}`);
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    async testCalendar() {
        const button = document.getElementById('test-calendar');
        
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch('/api/test-calendar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus('calendar-status', 'connected', data.message);
                this.showMessage('Google Calendar接続テスト成功', 'success');
                this.addLogEntry('success', 'Google Calendar接続テスト成功');
            } else {
                this.updateStatus('calendar-status', 'error', data.error);
                this.showMessage(`Google Calendar接続エラー: ${data.error}`, 'error');
                this.addLogEntry('error', `Google Calendar接続エラー: ${data.error}`);
            }
            
        } catch (error) {
            this.updateStatus('calendar-status', 'error', 'テスト失敗');
            this.showMessage(`Google Calendar接続テストエラー: ${error.message}`, 'error');
            this.addLogEntry('error', `Google Calendar接続テストエラー: ${error.message}`);
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    triggerOCRTest() {
        document.getElementById('ocr-file-input').click();
    }
    
    handleOCRFile(event) {
        const file = event.target.files[0];
        if (file) {
            this.processOCRFile(file);
        }
    }
    
    async processOCRFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showMessage('画像ファイルを選択してください', 'error');
            return;
        }
        
        const formData = new FormData();
        formData.append('image', file);
        
        this.updateStatus('ocr-status', 'loading', '処理中...');
        
        try {
            const response = await fetch('/api/test-ocr', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayOCRResults(data);
                this.updateStatus('ocr-status', 'connected', 'テスト成功');
                this.showMessage('OCRテスト成功', 'success');
                this.addLogEntry('success', `OCRテスト成功: ${data.found_dates.length}個の日付を検出`);
            } else {
                this.updateStatus('ocr-status', 'error', data.error);
                this.showMessage(`OCRテストエラー: ${data.error}`, 'error');
                this.addLogEntry('error', `OCRテストエラー: ${data.error}`);
            }
            
        } catch (error) {
            this.updateStatus('ocr-status', 'error', 'テスト失敗');
            this.showMessage(`OCRテストエラー: ${error.message}`, 'error');
            this.addLogEntry('error', `OCRテストエラー: ${error.message}`);
        }
    }
    
    displayOCRResults(data) {
        const resultsDiv = document.getElementById('ocr-results');
        const extractedText = document.getElementById('extracted-text');
        const foundDates = document.getElementById('found-dates');
        
        extractedText.textContent = data.extracted_text || '（テキストが検出されませんでした）';
        
        foundDates.innerHTML = '';
        if (data.found_dates && data.found_dates.length > 0) {
            data.found_dates.forEach(date => {
                const dateTag = document.createElement('span');
                dateTag.className = 'date-tag';
                dateTag.textContent = date;
                foundDates.appendChild(dateTag);
            });
        } else {
            foundDates.innerHTML = '<span style="color: #718096;">日付が検出されませんでした</span>';
        }
        
        resultsDiv.classList.remove('hidden');
    }
    
    async startMonitoring() {
        const button = document.getElementById('start-monitoring');
        
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch('/api/start-monitoring', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateStatus('monitoring-status', 'connected', '監視中');
                button.textContent = '監視中';
                button.disabled = true;
                this.showMessage('Slack監視を開始しました', 'success');
                this.addLogEntry('success', 'Slack監視を開始しました');
            } else {
                this.updateStatus('monitoring-status', 'error', data.error);
                this.showMessage(`監視開始エラー: ${data.error}`, 'error');
                this.addLogEntry('error', `監視開始エラー: ${data.error}`);
            }
            
        } catch (error) {
            this.updateStatus('monitoring-status', 'error', '開始失敗');
            this.showMessage(`監視開始エラー: ${error.message}`, 'error');
            this.addLogEntry('error', `監視開始エラー: ${error.message}`);
        } finally {
            this.setButtonLoading(button, false);
        }
    }
    
    checkSystemStatus() {
        // Initial status check
        this.addLogEntry('info', 'システム状態を確認中...');
        
        // You can add periodic status checks here
        setInterval(() => {
            // Periodic health checks if needed
        }, 30000); // Every 30 seconds
    }
    
    updateStatus(elementId, status, message) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        element.className = 'status-indicator';
        element.textContent = message;
        
        if (status === 'connected') {
            element.classList.add('connected');
        } else if (status === 'error') {
            element.classList.add('error');
        }
    }
    
    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.textContent = '処理中...';
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText || button.textContent;
        }
    }
    
    showMessage(message, type) {
        const messageDiv = document.getElementById('status-message');
        if (!messageDiv) return;
        
        messageDiv.textContent = message;
        messageDiv.className = `status-message ${type}`;
        messageDiv.classList.remove('hidden');
        
        setTimeout(() => {
            messageDiv.classList.add('hidden');
        }, 5000);
    }
    
    addLogEntry(type, message) {
        const logContent = document.getElementById('activity-log');
        if (!logContent) return;
        
        const timestamp = new Date().toLocaleTimeString('ja-JP');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `
            <span class="log-time">${timestamp}</span>
            <span class="log-message">${message}</span>
        `;
        
        logContent.insertBefore(logEntry, logContent.firstChild);
        
        // Keep only last 50 entries
        while (logContent.children.length > 50) {
            logContent.removeChild(logContent.lastChild);
        }
    }
    
    clearLog() {
        const logContent = document.getElementById('activity-log');
        if (logContent) {
            logContent.innerHTML = '';
            this.addLogEntry('info', 'ログをクリアしました');
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Slack2CalApp();
});