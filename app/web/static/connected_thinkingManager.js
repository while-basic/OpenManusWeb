// connected_thinkingManager.js - Manages the display of AI thinking process steps

import { t } from '/static/i18n.js';

export class ThinkingManager {
    constructor() {
        this.thinkingSteps = [];
        this.thinkingStepsContainer = null;
        this.clearButton = null;
        this.recordCount = null;
        this.refreshCountdown = null;
        this.autoRefresh = true;
        this.refreshIntervalId = null;
        this.refreshCountdownValue = 30;
    }

    init() {
        // Get DOM elements
        this.thinkingStepsContainer = document.getElementById('thinking-steps');
        this.clearButton = document.getElementById('clear-thinking');
        this.recordCount = document.getElementById('record-count');
        this.refreshCountdown = document.getElementById('refresh-countdown');

        // Initialize thinking steps
        this.thinkingSteps = [];
        this.renderThinkingSteps();

        // Bind events
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => {
                this.clearThinking();
            });
        }

        // Start auto-refresh
        this.startAutoRefresh();
    }

    // Add a new thinking step
    addThinkingStep(step) {
        // Add step to our tracking array
        this.thinkingSteps.push(step);
        
        // Render the updated thinking steps
        this.renderThinkingSteps();
    }

    // Render all thinking steps to the DOM
    renderThinkingSteps() {
        if (!this.thinkingStepsContainer) return;

        // Clear current content
        this.thinkingStepsContainer.innerHTML = '';

        if (this.thinkingSteps.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'empty-message';
            emptyMessage.textContent = t('no_thinking_steps');
            this.thinkingStepsContainer.appendChild(emptyMessage);
            
            // Update record count if element exists
            if (this.recordCount) {
                this.recordCount.textContent = '0';
            }
            return;
        }

        // Add each thinking step
        this.thinkingSteps.forEach((step, index) => {
            const stepElement = this.createThinkingStepElement(step, index);
            this.thinkingStepsContainer.appendChild(stepElement);
        });

        // Update record count if element exists
        if (this.recordCount) {
            this.recordCount.textContent = this.thinkingSteps.length.toString();
        }

        // Scroll to bottom
        this.thinkingStepsContainer.scrollTop = this.thinkingStepsContainer.scrollHeight;
    }

    // Create a DOM element for a thinking step
    createThinkingStepElement(step, index) {
        const stepElement = document.createElement('div');
        stepElement.className = 'thinking-step';
        
        // Create header with step number and timestamp
        const header = document.createElement('div');
        header.className = 'thinking-step-header';
        
        const stepNumber = document.createElement('div');
        stepNumber.className = 'thinking-step-number';
        stepNumber.textContent = `${t('step')} ${index + 1}`;
        
        const timestamp = document.createElement('div');
        timestamp.className = 'thinking-step-timestamp';
        const time = new Date(step.timestamp || Date.now()).toLocaleTimeString();
        timestamp.textContent = time;
        
        header.appendChild(stepNumber);
        header.appendChild(timestamp);
        
        // Create content for the step
        const content = document.createElement('div');
        content.className = 'thinking-step-content';
        
        // Format content based on step type
        if (step.type === 'thinking_step') {
            if (step.thought_number && step.total_thoughts) {
                content.innerHTML = `<strong>${t('thought')} ${step.thought_number}/${step.total_thoughts}:</strong> ${this.formatThinkingContent(step.content)}`;
            } else {
                content.innerHTML = this.formatThinkingContent(step.content);
            }
        } else {
            content.textContent = step.content || '';
        }
        
        // Assemble the step element
        stepElement.appendChild(header);
        stepElement.appendChild(content);
        
        return stepElement;
    }

    // Format thinking content with proper formatting
    formatThinkingContent(content) {
        if (!content) return '';
        
        // Convert links to clickable elements
        let formattedContent = content.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        );
        
        // Convert code blocks with syntax highlighting if available
        formattedContent = formattedContent.replace(
            /```([a-z]*)\n([\s\S]*?)\n```/g,
            '<pre class="code-block"><code class="language-$1">$2</code></pre>'
        );
        
        // Convert inline code
        formattedContent = formattedContent.replace(
            /`([^`]+)`/g,
            '<code>$1</code>'
        );
        
        return formattedContent;
    }

    // Clear all thinking steps
    clearThinking() {
        this.thinkingSteps = [];
        this.renderThinkingSteps();
    }

    // Start auto-refresh countdown
    startAutoRefresh() {
        if (this.refreshIntervalId) {
            clearInterval(this.refreshIntervalId);
        }

        this.refreshCountdownValue = 30;
        
        // Update countdown text if element exists
        if (this.refreshCountdown) {
            this.refreshCountdown.textContent = t('refresh_countdown', { seconds: this.refreshCountdownValue });
        }
        
        // Set up interval
        this.refreshIntervalId = setInterval(() => {
            this.refreshCountdownValue--;
            
            // Update countdown text
            if (this.refreshCountdown) {
                this.refreshCountdown.textContent = t('refresh_countdown', { seconds: this.refreshCountdownValue });
            }
            
            // When countdown reaches zero, refresh and reset
            if (this.refreshCountdownValue <= 0 && this.autoRefresh) {
                this.fetchLatestThinking();
                this.refreshCountdownValue = 30;
            }
        }, 1000);
    }

    // Fetch latest thinking steps from server
    async fetchLatestThinking() {
        try {
            const response = await fetch('/api/thinking');
            if (!response.ok) {
                throw new Error(t('api_error', { status: response.status }));
            }

            const data = await response.json();
            
            // Update thinking steps
            this.thinkingSteps = data.thinking_steps || [];
            this.renderThinkingSteps();
            
        } catch (error) {
            console.error(t('fetch_thinking_error', { message: error.message }), error);
        }
    }
}
