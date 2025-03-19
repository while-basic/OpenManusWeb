// connected_interface.js - Main JavaScript file responsible for initialization and coordination of other modules

// Import manager classes
import { WebSocketManager } from '/static/connected_websocketManager.js';
import { ChatManager } from '/static/connected_chatManager.js';
import { ThinkingManager } from '/static/connected_thinkingManager.js';
import { WorkspaceManager } from '/static/connected_workspaceManager.js';
import { FileViewerManager } from '/static/connected_fileViewerManager.js';
import { TerminalManager } from '/static/connected_terminalManager.js';
import { initLanguage, setLanguage, updatePageTexts, t } from '/static/i18n.js';
import { ErrorHandler, ErrorCategory, ErrorSeverity } from '/static/error_handler.js';

// Main application class
class App {
    constructor() {
        this.sessionId = null;
        this.isProcessing = false;

        // Initialize managers
        this.errorHandler = new ErrorHandler();
        this.websocketManager = new WebSocketManager(this.handleWebSocketMessage.bind(this), this.handleWebSocketError.bind(this));
        this.chatManager = new ChatManager(this.handleSendMessage.bind(this));
        this.thinkingManager = new ThinkingManager();
        this.workspaceManager = new WorkspaceManager(this.handleFileClick.bind(this));
        this.fileViewerManager = new FileViewerManager();
        this.terminalManager = new TerminalManager();

        // Bind UI events
        this.bindEvents();
    }

    // Initialize application
    init() {
        console.log('Sith Web application initializing...');

        // Initialize error handler
        this.errorHandler.init();

        // Initialize language settings
        const currentLang = initLanguage();
        document.getElementById('language-selector').value = currentLang;
        updatePageTexts();

        // Initialize managers
        this.chatManager.init();
        this.thinkingManager.init();
        this.workspaceManager.init();
        this.fileViewerManager.init();
        this.terminalManager.init();
        
        // Apply translations to dynamic elements
        this.updateDynamicTexts();

        // Load workspace files
        this.loadWorkspaceFiles();
    }

    // Bind UI events
    bindEvents() {
        // Stop button
        document.getElementById('stop-btn').addEventListener('click', () => {
            if (this.sessionId && this.isProcessing) {
                this.stopProcessing();
            }
        });

        // Clear button
        document.getElementById('clear-btn').addEventListener('click', () => {
            this.chatManager.clearMessages();
        });

        // Clear thinking records button
        document.getElementById('clear-thinking').addEventListener('click', () => {
            this.thinkingManager.clearThinking();
        });

        // Refresh files button
        document.getElementById('refresh-files').addEventListener('click', () => {
            this.loadWorkspaceFiles();
        });

        // Language selector
        document.getElementById('language-selector').addEventListener('change', (event) => {
            const selectedLang = event.target.value;
            setLanguage(selectedLang);
            updatePageTexts();
            this.updateDynamicTexts();
        });
    }

    // Update dynamically generated text
    updateDynamicTexts() {
        // Update status indicator
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator.textContent.includes('Processing')) {
            statusIndicator.textContent = t('processing_request');
        } else if (statusIndicator.textContent.includes('stopped')) {
            statusIndicator.textContent = t('processing_stopped');
        }

        // Update record count
        const recordCount = document.getElementById('record-count');
        const count = parseInt(recordCount.textContent);
        if (!isNaN(count)) {
            recordCount.textContent = t('records_count', { count });
        }

        // Update refresh countdown
        const refreshCountdown = document.getElementById('refresh-countdown');
        const seconds = refreshCountdown.textContent.match(/\d+/);
        if (seconds) {
            refreshCountdown.textContent = t('refresh_countdown', { seconds: seconds[0] });
        }
    }

    // Process sending message
    async handleSendMessage(message) {
        if (this.isProcessing) {
            this.errorHandler.showError(
                t('already_processing'),
                ErrorCategory.VALIDATION,
                ErrorSeverity.INFO
            );
            return;
        }

        this.isProcessing = true;
        document.getElementById('send-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
        document.getElementById('status-indicator').textContent = t('processing_request');

        try {
            // Send API request to create new session
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: message }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `${t('api_error')} (${response.status})`);
            }

            const data = await response.json();
            this.sessionId = data.session_id;

            // Add user message to chat
            this.chatManager.addUserMessage(message);

            // Connect WebSocket
            this.websocketManager.connect(this.sessionId);

            // Reset thinking records
            this.thinkingManager.clearThinking();

        } catch (error) {
            console.error(t('send_message_error', { message: error.message }), error);
            
            // Show error message
            this.errorHandler.showError(
                error.message || t('send_message_error_generic'),
                ErrorCategory.API,
                ErrorSeverity.ERROR
            );
            
            this.chatManager.addSystemMessage(t('error_occurred', { message: error.message }));
            
            // Reset state
            this.isProcessing = false;
            document.getElementById('send-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
            document.getElementById('status-indicator').textContent = t('processing_failed');
        }
    }

    // Handle WebSocket messages
    handleWebSocketMessage(data) {
        // Process different types of messages
        if (data.type === 'thinking') {
            this.thinkingManager.addThinkingStep(data);
        } else if (data.type === 'response') {
            this.chatManager.addAssistantMessage(data.content);
            this.finishProcessing();
        } else if (data.type === 'error') {
            this.errorHandler.showError(
                data.message || t('server_error'),
                ErrorCategory.SERVER,
                ErrorSeverity.ERROR
            );
            this.chatManager.addSystemMessage(t('error_occurred', { message: data.message }));
            this.finishProcessing();
        } else if (data.type === 'terminal_update' && data.error) {
            // Handle terminal errors
            if (data.error && data.error.trim()) {
                this.errorHandler.showError(
                    data.error,
                    ErrorCategory.TERMINAL,
                    ErrorSeverity.WARNING
                );
            }
        }
    }
    
    // Handle WebSocket errors
    handleWebSocketError(error) {
        this.errorHandler.showError(
            error.message || t('websocket_error'),
            ErrorCategory.WEBSOCKET,
            ErrorSeverity.ERROR
        );
    }

    // Stop processing
    async stopProcessing() {
        try {
            if (!this.sessionId) {
                return;
            }

            // Send API request to stop processing
            const response = await fetch(`/api/cancel/${this.sessionId}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `${t('api_error')} (${response.status})`);
            }

            this.chatManager.addSystemMessage(t('processing_stopped_message'));
            this.finishProcessing();

        } catch (error) {
            console.error(t('stop_processing_error', { message: error.message }), error);
            
            // Show error message
            this.errorHandler.showError(
                error.message || t('stop_processing_error_generic'),
                ErrorCategory.API,
                ErrorSeverity.ERROR
            );
            
            this.chatManager.addSystemMessage(t('error_occurred', { message: error.message }));
            this.finishProcessing();
        }
    }

    // Finish processing
    finishProcessing() {
        this.isProcessing = false;
        document.getElementById('send-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
        document.getElementById('status-indicator').textContent = '';
    }

    // Load workspace files
    async loadWorkspaceFiles() {
        try {
            const response = await fetch('/api/files');
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `${t('api_error')} (${response.status})`);
            }
            
            const data = await response.json();
            this.workspaceManager.updateWorkspaces(data.workspaces);
            
        } catch (error) {
            console.error(t('load_files_error', { message: error.message }), error);
            
            // Show error message
            this.errorHandler.showError(
                error.message || t('load_files_error_generic'),
                ErrorCategory.FILE_SYSTEM,
                ErrorSeverity.ERROR
            );
        }
    }

    // Handle file click
    async handleFileClick(filePath) {
        try {
            // Load file content
            const response = await fetch(`/api/file?path=${encodeURIComponent(filePath)}`);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `${t('api_error')} (${response.status})`);
            }
            
            const data = await response.json();
            
            if (!data.content && data.content !== '') {
                throw new Error(t('file_empty_error'));
            }
            
            // Display file content
            this.fileViewerManager.showFile(filePath, data.content);
            
        } catch (error) {
            console.error(t('load_file_error', { message: error.message }), error);
            
            // Show error message
            this.errorHandler.showError(
                error.message || t('load_file_error_generic', { file: filePath }),
                ErrorCategory.FILE_SYSTEM,
                ErrorSeverity.ERROR
            );
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init();
    
    // Expose app to window for debugging
    window.app = app;
});
