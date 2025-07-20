class MarkdSlideApp {
    constructor() {
        this.slides = [];
        this.currentSlide = 0;
        this.timer = null;
        this.timeLeft = 0;
        this.bonusTime = 0;
        this.isFullscreen = false;
        this.isPresentationMode = false;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadInitialContent();
    }
    
    initializeElements() {
        // Editor elements
        this.markdownInput = document.getElementById('markdown-input');
        this.previewArea = document.getElementById('preview-area');
        this.startBtn = document.getElementById('start-presentation');
        this.saveBtn = document.getElementById('save-btn');
        this.loadBtn = document.getElementById('load-btn');
        this.fileInput = document.getElementById('file-input');
        
        // Presentation elements
        this.presentationMode = document.getElementById('presentation-mode');
        this.slideContent = document.getElementById('slide-content');
        this.currentSlideSpan = document.getElementById('current-slide');
        this.totalSlidesSpan = document.getElementById('total-slides');
        this.timerDisplay = document.getElementById('timer');
        this.progressFill = document.getElementById('progress-fill');
        
        // Control buttons
        this.exitBtn = document.getElementById('exit-presentation');
        this.fullscreenBtn = document.getElementById('toggle-fullscreen');
        this.prevBtn = document.getElementById('prev-slide');
        this.nextBtn = document.getElementById('next-slide');
        
        // Audio
        this.slideSound = document.getElementById('slide-sound');
    }
    
    setupEventListeners() {
        // Editor events
        this.markdownInput.addEventListener('input', () => this.updatePreview());
        this.startBtn.addEventListener('click', () => this.startPresentation());
        this.saveBtn.addEventListener('click', () => this.saveFile());
        this.loadBtn.addEventListener('click', () => this.loadFile());
        this.fileInput.addEventListener('change', (e) => this.handleFileLoad(e));
        
        // Presentation events
        this.exitBtn.addEventListener('click', () => this.exitPresentation());
        this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        this.prevBtn.addEventListener('click', () => this.previousSlide());
        this.nextBtn.addEventListener('click', () => this.nextSlide());
        
        // Keyboard events
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        // Prevent context menu in presentation mode
        document.addEventListener('contextmenu', (e) => {
            if (this.isPresentationMode) {
                e.preventDefault();
            }
        });
    }
    
    loadInitialContent() {
        this.updatePreview();
    }
    
    async updatePreview() {
        const markdown = this.markdownInput.value;
        try {
            const response = await fetch('/parse_slides', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ markdown })
            });
            
            const data = await response.json();
            this.slides = data.slides;
            
            // Show first slide in preview
            if (this.slides.length > 0) {
                this.previewArea.innerHTML = this.slides[0].html;
            }
            
            // Highlight code blocks
            this.previewArea.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
            
        } catch (error) {
            console.error('Error parsing slides:', error);
            this.previewArea.innerHTML = '<p style="color: red;">Error parsing markdown</p>';
        }
    }
    
    async startPresentation() {
        if (this.slides.length === 0) {
            alert('スライドがありません。まずMarkdownを入力してください。');
            return;
        }
        
        this.isPresentationMode = true;
        this.currentSlide = 0;
        this.bonusTime = 0;
        
        // Hide main container and show presentation mode
        document.getElementById('main-container').style.display = 'none';
        this.presentationMode.style.display = 'flex';
        
        // Update slide counter
        this.totalSlidesSpan.textContent = this.slides.length;
        
        // Show first slide
        this.showSlide(0);
        
        // Play start sound
        this.playSlideSound();
        
        // Request fullscreen if supported
        if (document.documentElement.requestFullscreen) {
            try {
                await document.documentElement.requestFullscreen();
                this.isFullscreen = true;
                document.body.classList.add('fullscreen');
            } catch (err) {
                console.log('Fullscreen not supported or denied');
            }
        }
    }
    
    exitPresentation() {
        this.isPresentationMode = false;
        this.stopTimer();
        
        // Show main container and hide presentation mode
        document.getElementById('main-container').style.display = 'block';
        this.presentationMode.style.display = 'none';
        
        // Exit fullscreen
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }
        this.isFullscreen = false;
        document.body.classList.remove('fullscreen');
    }
    
    showSlide(index) {
        if (index < 0 || index >= this.slides.length) return;
        
        const slide = this.slides[index];
        this.currentSlide = index;
        
        // Update slide content with animation
        this.slideContent.style.animation = 'slideIn 0.6s ease-out';
        this.slideContent.innerHTML = slide.html;
        
        // Highlight code blocks
        this.slideContent.querySelectorAll('pre code').forEach(block => {
            hljs.highlightElement(block);
        });
        
        // Update counter
        this.currentSlideSpan.textContent = index + 1;
        
        // Update progress bar
        const progress = ((index + 1) / this.slides.length) * 100;
        this.progressFill.style.width = `${progress}%`;
        
        // Update navigation buttons
        this.prevBtn.disabled = index === 0;
        this.nextBtn.disabled = index === this.slides.length - 1;
        
        // Start timer
        this.startTimer(slide.timing);
        
    }
    
    startTimer(seconds) {
        this.stopTimer();
        const usedBonusTime = this.bonusTime; // Store bonus time before resetting
        this.timeLeft = seconds + this.bonusTime;
        this.bonusTime = 0; // Reset bonus time after using it
        
        // Update display to show used bonus time
        this.updateTimerDisplay(usedBonusTime);
        
        this.timer = setInterval(() => {
            this.timeLeft--;
            this.updateTimerDisplay(usedBonusTime);
            
            if (this.timeLeft <= 0) {
                this.stopTimer();
                // Auto-advance to next slide if available
                if (this.currentSlide < this.slides.length - 1) {
                    this.nextSlide();
                }
            }
        }, 1000);
    }
    
    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    
    updateTimerDisplay(usedBonusTime = 0) {
        const minutes = Math.floor(this.timeLeft / 60);
        const seconds = this.timeLeft % 60;
        
        let displayText = `${minutes}分${seconds}秒`;
        if (usedBonusTime > 0) {
            displayText += `(+${usedBonusTime}秒)`;
        }
        this.timerDisplay.textContent = displayText;
        
        // Update timer color based on remaining time
        this.timerDisplay.classList.remove('warning', 'danger');
        if (this.timeLeft <= 10) {
            this.timerDisplay.classList.add('danger');
        } else if (this.timeLeft <= 30) {
            this.timerDisplay.classList.add('warning');
        }
    }
    
    previousSlide() {
        if (this.currentSlide > 0) {
            // Stop current timer without adding bonus time (going backwards)
            this.stopTimer();
            this.showSlide(this.currentSlide - 1);
            this.playSlideSound();
        }
    }
    
    nextSlide() {
        if (this.currentSlide < this.slides.length - 1) {
            // Add any remaining time as bonus (only when going forward)
            if (this.timeLeft > 0) {
                this.bonusTime += this.timeLeft;
            }
            this.showSlide(this.currentSlide + 1);
            this.playSlideSound();
        }
    }
    
    async toggleFullscreen() {
        if (this.isFullscreen) {
            if (document.exitFullscreen) {
                await document.exitFullscreen();
            }
            this.isFullscreen = false;
            document.body.classList.remove('fullscreen');
            this.fullscreenBtn.textContent = '🔍 全画面';
        } else {
            if (document.documentElement.requestFullscreen) {
                await document.documentElement.requestFullscreen();
            }
            this.isFullscreen = true;
            document.body.classList.add('fullscreen');
            this.fullscreenBtn.textContent = '🔍 ウィンドウ';
        }
    }
    
    handleKeyboard(event) {
        if (!this.isPresentationMode) return;
        
        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                this.previousSlide();
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.nextSlide();
                break;
            case 'f':
            case 'F':
                event.preventDefault();
                this.toggleFullscreen();
                break;
            case 'Escape':
                event.preventDefault();
                this.exitPresentation();
                break;
        }
    }
    
    playSlideSound() {
        if (this.slideSound) {
            this.slideSound.currentTime = 0;
            this.slideSound.play().catch(e => {
                // Ignore audio play errors (user hasn't interacted with page yet)
            });
        }
    }
    
    async saveFile() {
        const content = this.markdownInput.value;
        const filename = prompt('ファイル名を入力してください:', 'presentation.md');
        
        if (!filename) return;
        
        try {
            const response = await fetch('/save_file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content, filename })
            });
            
            const data = await response.json();
            if (data.success) {
                alert('ファイルが保存されました: ' + filename);
            } else {
                alert('保存に失敗しました');
            }
        } catch (error) {
            console.error('Error saving file:', error);
            alert('保存中にエラーが発生しました');
        }
    }
    
    loadFile() {
        this.fileInput.click();
    }
    
    async handleFileLoad(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/load_file', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.content) {
                this.markdownInput.value = data.content;
                this.updatePreview();
                alert('ファイルが読み込まれました');
            } else {
                alert('ファイルの読み込みに失敗しました: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error loading file:', error);
            alert('ファイル読み込み中にエラーが発生しました');
        }
        
        // Reset file input
        event.target.value = '';
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MarkdSlideApp();
});