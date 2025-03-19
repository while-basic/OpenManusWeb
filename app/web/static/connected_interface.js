// connected_interface.js - Main JavaScript file responsible for initialization and coordination of other modules

// Import manager classes
import { WebSocketManager } from '/static/connected_websocketManager.js';
import { ChatManager } from '/static/connected_chatManager.js';
import { ThinkingManager } from '/static/connected_thinkingManager.js';
import { WorkspaceManager } from '/static/connected_workspaceManager.js';
import { FileViewerManager } from '/static/connected_fileViewerManager.js';
import { TerminalManager } from '/static/connected_terminalManager.js';
import { initLanguage, setLanguage, updatePageTexts, t } from '/static/i18n.js';

// Main application class
class App {
    constructor() {
        this.sessionId = null;
        this.isProcessing = false;

        // Initialize managers
        this.websocketManager = new WebSocketManager(this.handleWebSocketMessage.bind(this));
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
        console.log('OpenManus Web application initializing...');

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
            console.log('Processing, please wait...');
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
                throw new Error(t('api_error', { status: response.status }));
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
            this.chatManager.addSystemMessage(t('error_occurred', { message: error.message }));
            this.isProcessing = false;
            document.getElementById('send-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
            document.getElementById('status-indicator').textContent = '';
        }
    }

    // Process WebSocket message
    handleWebSocketMessage(data) {
        if (data.type === 'thinking_step') {
            this.thinkingManager.addThinkingStep(data);
        } else if (data.type === 'ai_message') {
            this.chatManager.addAIMessage(data.content);
        } else if (data.type === 'file_generated') {
            // Update file list
            this.workspaceManager.addFile(data.file);
        } else if (data.type === 'terminal_update') {
            // Handle terminal update
            this.terminalManager.handleTerminalUpdate(data);
        } else if (data.type === 'completed') {
            this.processingComplete();
        }
    }

    // Stop processing
    async stopProcessing() {
        if (!this.sessionId) return;

        try {
            const response = await fetch(`/api/chat/${this.sessionId}/stop`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error(t('api_error', { status: response.status }));
            }

            console.log('Processing stopped');
            this.chatManager.addSystemMessage(t('processing_stopped'));
            document.getElementById('status-indicator').textContent = t('processing_stopped');
            document.getElementById('send-btn').disabled = false;
            document.getElementById('stop-btn').disabled = true;
            this.isProcessing = false;

        } catch (error) {
            console.error(t('stop_processing_error', { message: error.message }), error);
            this.chatManager.addSystemMessage(t('error_occurred', { message: error.message }));
        }
    }

    // Load workspace files
    async loadWorkspaceFiles() {
        try {
            const response = await fetch('/api/files');
            if (!response.ok) {
                throw new Error(t('api_error', { status: response.status }));
            }

            const data = await response.json();
            this.workspaceManager.updateWorkspaces(data.workspaces);

        } catch (error) {
            console.error(t('load_workspace_error', { message: error.message }), error);
        }
    }

    // Handle file click
    async handleFileClick(filePath) {
        try {
            const response = await fetch(`/api/files/${encodeURIComponent(filePath)}`);
            if (!response.ok) {
                throw new Error(t('api_error', { status: response.status }));
            }

            const data = await response.json();
            this.fileViewerManager.showFile(data.name, data.content);

        } catch (error) {
            console.error(t('load_file_error', { message: error.message }), error);
            this.chatManager.addSystemMessage(t('error_occurred', { message: error.message }));
        }
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init();

    // Expose app instance to global for debugging
    window.app = app;
});
