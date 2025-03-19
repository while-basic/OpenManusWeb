// error_handler.js - Centralized error handling for the web interface

/**
 * Error categories for consistent error classification
 */
export const ErrorCategory = {
    NETWORK: 'network',
    API: 'api',
    WEBSOCKET: 'websocket',
    AUTHENTICATION: 'auth',
    VALIDATION: 'validation',
    SERVER: 'server',
    TERMINAL: 'terminal',
    FILE_SYSTEM: 'file_system',
    GENERAL: 'general'
};

/**
 * Error severity levels
 */
export const ErrorSeverity = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error',
    CRITICAL: 'critical'
};

/**
 * Class for handling and displaying errors in the UI
 */
export class ErrorHandler {
    constructor() {
        this.errorContainer = null;
        this.dismissTimeout = null;
        this.errors = [];
    }

    /**
     * Initialize the error handler
     */
    init() {
        // Create error container if it doesn't exist
        if (!document.getElementById('error-container')) {
            this.errorContainer = document.createElement('div');
            this.errorContainer.id = 'error-container';
            document.body.appendChild(this.errorContainer);
            
            // Add styles to error container
            this.errorContainer.style.position = 'fixed';
            this.errorContainer.style.top = '20px';
            this.errorContainer.style.right = '20px';
            this.errorContainer.style.zIndex = '1000';
            this.errorContainer.style.maxWidth = '400px';
            this.errorContainer.style.maxHeight = '80vh';
            this.errorContainer.style.overflowY = 'auto';
            this.errorContainer.style.display = 'flex';
            this.errorContainer.style.flexDirection = 'column';
            this.errorContainer.style.gap = '10px';
        } else {
            this.errorContainer = document.getElementById('error-container');
        }
    }

    /**
     * Show an error message
     * @param {string} message - Error message
     * @param {string} category - Error category from ErrorCategory
     * @param {string} severity - Error severity from ErrorSeverity
     * @param {number} timeout - Auto-dismiss timeout in ms (0 for no auto-dismiss)
     */
    showError(message, category = ErrorCategory.GENERAL, severity = ErrorSeverity.ERROR, timeout = 5000) {
        // Create error element
        const errorElement = document.createElement('div');
        errorElement.className = `error-message ${severity} ${category}`;
        
        // Create header with category and close button
        const header = document.createElement('div');
        header.className = 'error-header';
        header.innerHTML = `
            <span class="error-category">${this.formatCategory(category)}</span>
            <button class="error-close">×</button>
        `;
        
        // Create message body
        const body = document.createElement('div');
        body.className = 'error-body';
        body.textContent = message;
        
        // Add elements to error container
        errorElement.appendChild(header);
        errorElement.appendChild(body);
        
        // Style the error element
        this.applyErrorStyles(errorElement, severity);
        
        // Add close button functionality
        const closeButton = errorElement.querySelector('.error-close');
        closeButton.addEventListener('click', () => {
            this.removeError(errorElement);
        });
        
        // Add error to container
        this.errorContainer.appendChild(errorElement);
        
        // Store error in array
        this.errors.push(errorElement);
        
        // Auto-dismiss if timeout is set
        if (timeout > 0) {
            setTimeout(() => {
                this.removeError(errorElement);
            }, timeout);
        }
        
        // Log error to console
        console.error(`[${this.formatCategory(category)}] ${message}`);
        
        return errorElement;
    }
    
    /**
     * Remove an error element
     * @param {HTMLElement} errorElement - The error element to remove
     */
    removeError(errorElement) {
        // Add fade-out animation
        errorElement.style.opacity = '0';
        
        // Remove after animation
        setTimeout(() => {
            if (errorElement.parentNode === this.errorContainer) {
                this.errorContainer.removeChild(errorElement);
                this.errors = this.errors.filter(e => e !== errorElement);
            }
        }, 300);
    }
    
    /**
     * Clear all errors
     */
    clearAllErrors() {
        while (this.errorContainer.firstChild) {
            this.errorContainer.removeChild(this.errorContainer.firstChild);
        }
        this.errors = [];
    }
    
    /**
     * Format category for display
     * @param {string} category - Error category
     * @returns {string} Formatted category
     */
    formatCategory(category) {
        switch (category) {
            case ErrorCategory.NETWORK: return 'Network Error';
            case ErrorCategory.API: return 'API Error';
            case ErrorCategory.WEBSOCKET: return 'WebSocket Error';
            case ErrorCategory.AUTHENTICATION: return 'Authentication Error';
            case ErrorCategory.VALIDATION: return 'Validation Error';
            case ErrorCategory.SERVER: return 'Server Error';
            case ErrorCategory.TERMINAL: return 'Terminal Error';
            case ErrorCategory.FILE_SYSTEM: return 'File System Error';
            default: return 'Error';
        }
    }
    
    /**
     * Apply styles to error element based on severity
     * @param {HTMLElement} errorElement - The error element
     * @param {string} severity - Error severity
     */
    applyErrorStyles(errorElement, severity) {
        // Base styles
        errorElement.style.backgroundColor = 'white';
        errorElement.style.borderRadius = '8px';
        errorElement.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
        errorElement.style.transition = 'opacity 0.3s ease';
        errorElement.style.overflow = 'hidden';
        
        // Header styles
        const header = errorElement.querySelector('.error-header');
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        header.style.padding = '10px 15px';
        header.style.fontWeight = 'bold';
        
        // Close button styles
        const closeButton = errorElement.querySelector('.error-close');
        closeButton.style.background = 'none';
        closeButton.style.border = 'none';
        closeButton.style.fontSize = '18px';
        closeButton.style.cursor = 'pointer';
        closeButton.style.color = 'inherit';
        
        // Body styles
        const body = errorElement.querySelector('.error-body');
        body.style.padding = '10px 15px 15px';
        body.style.wordBreak = 'break-word';
        
        // Apply severity-specific styles
        switch (severity) {
            case ErrorSeverity.INFO:
                errorElement.style.borderLeft = '5px solid #3498db';
                header.style.backgroundColor = '#ebf5fb';
                header.style.color = '#2980b9';
                closeButton.style.color = '#2980b9';
                break;
                
            case ErrorSeverity.WARNING:
                errorElement.style.borderLeft = '5px solid #f39c12';
                header.style.backgroundColor = '#fef5e7';
                header.style.color = '#d35400';
                closeButton.style.color = '#d35400';
                break;
                
            case ErrorSeverity.ERROR:
                errorElement.style.borderLeft = '5px solid #e74c3c';
                header.style.backgroundColor = '#fdedec';
                header.style.color = '#c0392b';
                closeButton.style.color = '#c0392b';
                break;
                
            case ErrorSeverity.CRITICAL:
                errorElement.style.borderLeft = '5px solid #8e44ad';
                header.style.backgroundColor = '#f4ecf7';
                header.style.color = '#6c3483';
                closeButton.style.color = '#6c3483';
                break;
        }
    }
} 