class Web2MarkdApp {
    constructor() {
        this.currentContent = '';
        this.currentFilename = '';
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadFiles();
    }
    
    bindEvents() {
        // URL crawling
        document.getElementById('crawl-btn').addEventListener('click', () => this.crawlUrl());
        document.getElementById('url-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.crawlUrl();
        });
        
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        
        // Save content
        document.getElementById('save-btn').addEventListener('click', () => this.saveContent());
        
        // File management
        document.getElementById('refresh-files').addEventListener('click', () => this.loadFiles());
    }
    
    async crawlUrl() {
        const urlInput = document.getElementById('url-input');
        const url = urlInput.value.trim();
        
        if (!url) {
            this.showStatus('URLを入力してください', 'error');
            return;
        }
        
        try {
            this.showLoading(true);
            this.hideStatus();
            this.hideContentSection();
            
            // Collect filter options
            const filterOptions = this.collectFilterOptions();
            
            console.log('Starting crawl for:', url);
            console.log('Filter options:', filterOptions);
            
            const response = await fetch('/crawl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    filter_options: filterOptions
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentContent = data.content;
                this.displayContent(data);
                this.showStatus(`✅ コンテンツを取得しました (${data.content_length}文字)`, 'success');
                this.showContentSection();
            } else {
                this.showStatus(`❌ エラー: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Crawl error:', error);
            this.showStatus(`❌ クロールに失敗しました: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    collectFilterOptions() {
        const options = {};
        
        // Remove ads checkbox
        options.remove_ads = document.getElementById('remove-ads').checked;
        
        // Remove selectors
        const removeSelectors = document.getElementById('remove-selectors').value.trim();
        if (removeSelectors) {
            options.remove_selectors = removeSelectors.split(',').map(s => s.trim()).filter(s => s);
        }
        
        // Keep selectors
        const keepSelectors = document.getElementById('keep-selectors').value.trim();
        if (keepSelectors) {
            options.keep_selectors = keepSelectors.split(',').map(s => s.trim()).filter(s => s);
        }
        
        // Remove tags
        const removeTags = document.getElementById('remove-tags').value.trim();
        if (removeTags) {
            options.remove_tags = removeTags.split(',').map(s => s.trim()).filter(s => s);
        }
        
        return options;
    }
    
    displayContent(data) {
        // Update title and info
        document.getElementById('content-title').textContent = data.title || 'Webコンテンツ';
        document.getElementById('content-length').textContent = `${data.content_length}文字`;
        document.getElementById('content-url').textContent = data.url;
        
        // Show preview
        document.getElementById('content-preview').textContent = data.preview;
        
        // Show full markdown
        document.getElementById('markdown-content').value = data.content;
        
        // Generate filename suggestion
        const domain = new URL(data.url).hostname.replace('www.', '');
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
        const suggestedFilename = `${domain}_${timestamp}.md`;
        document.getElementById('filename-input').value = suggestedFilename;
    }
    
    async saveContent() {
        if (!this.currentContent) {
            this.showStatus('保存するコンテンツがありません', 'error');
            return;
        }
        
        const filename = document.getElementById('filename-input').value.trim();
        
        try {
            const response = await fetch('/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: this.currentContent,
                    filename: filename
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showStatus(`✅ ${data.message}`, 'success');
                this.currentFilename = data.filename;
                this.showDownloadButton();
                this.loadFiles(); // Refresh file list
            } else {
                this.showStatus(`❌ 保存エラー: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Save error:', error);
            this.showStatus(`❌ 保存に失敗しました: ${error.message}`, 'error');
        }
    }
    
    async loadFiles() {
        try {
            const response = await fetch('/files');
            const data = await response.json();
            
            if (data.files) {
                this.displayFiles(data.files);
            } else {
                console.error('Failed to load files:', data.error);
            }
            
        } catch (error) {
            console.error('Load files error:', error);
        }
    }
    
    displayFiles(files) {
        const filesList = document.getElementById('files-list');
        
        if (files.length === 0) {
            filesList.innerHTML = '<p class="text-center" style="color: #718096;">保存されたファイルはありません</p>';
            return;
        }
        
        filesList.innerHTML = files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">📄 ${file.filename}</div>
                    <div class="file-meta">${this.formatFileSize(file.size)} • ${file.modified}</div>
                </div>
                <div class="file-actions">
                    <a href="/download/${file.filename}" class="btn btn-small btn-secondary">⬇️ ダウンロード</a>
                </div>
            </div>
        `).join('');
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    showLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }
    
    showStatus(message, type) {
        const statusMessage = document.getElementById('status-message');
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
        statusMessage.style.display = 'block';
    }
    
    hideStatus() {
        const statusMessage = document.getElementById('status-message');
        statusMessage.style.display = 'none';
    }
    
    showContentSection() {
        document.getElementById('content-section').classList.remove('hidden');
    }
    
    hideContentSection() {
        document.getElementById('content-section').classList.add('hidden');
    }
    
    showDownloadButton() {
        document.getElementById('download-btn').classList.remove('hidden');
        document.getElementById('download-btn').onclick = () => {
            window.open(`/download/${this.currentFilename}`, '_blank');
        };
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Web2MarkdApp();
});