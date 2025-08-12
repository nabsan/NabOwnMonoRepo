class ConfigManager {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupDatePatterns();
    }
    
    bindEvents() {
        // Form submission
        document.getElementById('config-form')?.addEventListener('submit', (e) => this.saveConfig(e));
        
        // Reset config
        document.getElementById('reset-config')?.addEventListener('click', () => this.resetConfig());
        
        // Add pattern button
        document.getElementById('add-pattern')?.addEventListener('click', () => this.addDatePattern());
        
        // Remove pattern buttons (delegated)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-pattern')) {
                this.removeDatePattern(e.target);
            }
        });
    }
    
    setupDatePatterns() {
        // Add event listeners to existing pattern remove buttons
        document.querySelectorAll('.remove-pattern').forEach(button => {
            button.addEventListener('click', () => this.removeDatePattern(button));
        });
    }
    
    async saveConfig(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const config = {};
        
        // Process form data into nested object structure
        for (const [key, value] of formData.entries()) {
            this.setNestedValue(config, key, value);
        }
        
        // Handle date patterns separately
        const datePatterns = [];
        document.querySelectorAll('.pattern-input').forEach(input => {
            if (input.value.trim()) {
                datePatterns.push(input.value.trim());
            }
        });
        this.setNestedValue(config, 'ocr.date_patterns', datePatterns);
        
        // Convert string numbers to actual numbers
        this.convertNumbers(config);
        
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('設定が正常に保存されました', 'success');
                // Optionally reload the page to reflect changes
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.showMessage(`設定保存エラー: ${result.error}`, 'error');
            }
            
        } catch (error) {
            this.showMessage(`設定保存エラー: ${error.message}`, 'error');
        }
    }
    
    async resetConfig() {
        if (!confirm('設定をデフォルト値にリセットしますか？この操作は元に戻せません。')) {
            return;
        }
        
        try {
            // Load default configuration
            const defaultConfig = {
                slack: {
                    workspace_name: 'myown',
                    channel_name: 'calendar',
                    bot_token: '',
                    app_token: ''
                },
                google_calendar: {
                    calendar_id: 'primary',
                    credentials_file: 'config/google_credentials.json',
                    token_file: 'config/google_token.json'
                },
                ocr: {
                    language: 'jpn+eng',
                    date_patterns: ['%Y年%m月%d日', '%Y/%m/%d', '%Y-%m-%d', '%m月%d日', '%m/%d']
                },
                app: {
                    port: 5002,
                    debug: true,
                    log_level: 'INFO',
                    image_download_timeout: 30,
                    temp_folder: 'temp'
                },
                event: {
                    default_title: 'スケジュール',
                    default_duration_hours: 1,
                    default_time: '09:00'
                }
            };
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(defaultConfig)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('設定をデフォルト値にリセットしました', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                this.showMessage(`設定リセットエラー: ${result.error}`, 'error');
            }
            
        } catch (error) {
            this.showMessage(`設定リセットエラー: ${error.message}`, 'error');
        }
    }
    
    addDatePattern() {
        const patternsContainer = document.querySelector('.date-patterns');
        if (!patternsContainer) return;
        
        const patternItem = document.createElement('div');
        patternItem.className = 'pattern-item';
        patternItem.innerHTML = `
            <input type="text" value="" class="pattern-input" placeholder="%Y年%m月%d日">
            <button type="button" class="btn btn-small remove-pattern">削除</button>
        `;
        
        patternsContainer.appendChild(patternItem);
    }
    
    removeDatePattern(button) {
        const patternItem = button.closest('.pattern-item');
        if (patternItem) {
            patternItem.remove();
        }
    }
    
    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!(key in current)) {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
    }
    
    convertNumbers(obj) {
        // Convert string numbers to actual numbers for specific fields
        const numberFields = [
            'app.port',
            'app.image_download_timeout',
            'event.default_duration_hours'
        ];
        
        numberFields.forEach(field => {
            const value = this.getNestedValue(obj, field);
            if (value !== undefined && !isNaN(value)) {
                this.setNestedValue(obj, field, Number(value));
            }
        });
        
        // Convert boolean fields
        const booleanFields = [
            'app.debug'
        ];
        
        booleanFields.forEach(field => {
            const value = this.getNestedValue(obj, field);
            if (value !== undefined) {
                this.setNestedValue(obj, field, value === 'true' || value === true);
            }
        });
    }
    
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
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
}

// Initialize the configuration manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ConfigManager();
});