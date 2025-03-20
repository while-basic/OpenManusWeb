// chat.js - Simple chat interface handler

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat.js loaded - initializing chat interface');
    initChatInterface();
});

// Initialize chat interface
function initChatInterface() {
    const sendButton = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');
    const stopButton = document.getElementById('stop-btn');
    const chatMessages = document.getElementById('chat-messages');
    
    // Check if elements exist
    if (!sendButton || !userInput || !chatMessages) {
        console.error('Chat interface elements not found!');
        return;
    }
    
    console.log('Chat interface elements found - attaching event handlers');
    
    // Send button click event
    sendButton.addEventListener('click', function() {
        const message = userInput.value.trim();
        if (message) {
            sendMessage(message);
        }
    });
    
    // Enter key event
    userInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            const message = userInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        }
    });
    
    // Stop button click event
    if (stopButton) {
        stopButton.addEventListener('click', stopProcessing);
        stopButton.disabled = true;
    }
    
    // Clear button click event
    const clearButton = document.getElementById('clear-btn');
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            if (chatMessages) {
                chatMessages.innerHTML = '';
            }
        });
    }
    
    // Initialize WebSocket
    initWebSocket();
}

// Send message function
async function sendMessage(message) {
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const stopButton = document.getElementById('stop-btn');
    const chatMessages = document.getElementById('chat-messages');
    const statusIndicator = document.getElementById('status-indicator');
    
    // Add user message to chat
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = message;
    
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Clear input
    userInput.value = '';
    
    // Disable send button and enable stop button
    sendButton.disabled = true;
    if (stopButton) stopButton.disabled = false;
    
    // Update status
    if (statusIndicator) statusIndicator.textContent = 'Processing...';
    
    console.log('Sending message:', message);
    
    try {
        // Send message to server
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: message })
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        // Set session ID and reconnect WebSocket with new session ID
        if (data.session_id) {
            // Update URL with session ID
            const url = new URL(window.location);
            url.searchParams.set('session_id', data.session_id);
            window.history.pushState({}, '', url);
            
            // Close existing WebSocket if it exists
            if (window.socket && window.socket.readyState === WebSocket.OPEN) {
                window.socket.close();
            }
            
            // Connect with the new session ID after a short delay
            setTimeout(connect, 500);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        addSystemErrorMessage(error.message);
        if (statusIndicator) statusIndicator.textContent = 'Error';
        sendButton.disabled = false;
        if (stopButton) stopButton.disabled = true;
    }
}

// Stop processing function
async function stopProcessing() {
    console.log('Attempting to stop processing...');
    
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        console.log('No session ID found, cannot stop processing');
        return;
    }
    
    console.log('Stopping session:', sessionId);
    
    try {
        const response = await fetch(`/api/chat/${sessionId}/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Stop response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) statusIndicator.textContent = 'Processing stopped';
        
        addSystemMessage('Processing stopped by user');
        
        // Update UI state
        const sendButton = document.getElementById('send-btn');
        const stopButton = document.getElementById('stop-btn');
        if (sendButton) sendButton.disabled = false;
        if (stopButton) stopButton.disabled = true;
    } catch (error) {
        console.error('Error stopping processing:', error);
        addSystemErrorMessage('Failed to stop processing: ' + error.message);
    }
}

// WebSocket implementation
let socket = null;

// Initialize WebSocket connection
function initWebSocket() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        console.log('No session ID found, WebSocket connection not established');
        return;
    }
    
    // Connect to WebSocket
    connect();
}

// Connect to WebSocket
function connect() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        console.log('No session ID found, WebSocket connection not established');
        return;
    }
    
    console.log('Connecting to WebSocket with session ID:', sessionId);
    
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/${sessionId}`;
    
    console.log('WebSocket URL:', wsUrl);
    
    window.socket = new WebSocket(wsUrl);
    
    window.socket.onopen = function() {
        console.log('WebSocket connection established');
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) statusIndicator.textContent = 'Connected';
    };
    
    window.socket.onclose = function(event) {
        console.log('WebSocket connection closed', event);
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) statusIndicator.textContent = 'Disconnected';
        
        // Try to reconnect if not a normal closure
        if (event.code !== 1000) {
            setTimeout(connect, 2000);
        }
    };
    
    window.socket.onerror = function(error) {
        console.error('WebSocket error:', error);
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) statusIndicator.textContent = 'Connection Error';
    };
    
    window.socket.onmessage = function(event) {
        console.log('WebSocket message received:', event.data);
        
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error, event.data);
        }
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    console.log('Processing WebSocket message:', data);
    
    if (data.type === 'thinking' || data.type === 'thinking_step') {
        // Handle thinking step
        addThinkingStep(data);
    } 
    else if (data.type === 'response' || data.type === 'ai_message') {
        // Handle assistant response
        addAIMessage(data.content);
        markProcessingComplete();
    } 
    else if (data.type === 'error') {
        // Handle error message
        addSystemErrorMessage(data.message || 'An error occurred');
        markProcessingComplete();
    } 
    else if (data.type === 'terminal_update') {
        // Handle terminal output
        updateTerminal(data);
    } 
    else if (data.type === 'system_logs') {
        // Handle system logs update
        updateSystemLogs(data.logs);
    } 
    else if (data.type === 'file_generated') {
        // Handle generated file
        addGeneratedFile(data.file);
    }
    else if (data.type === 'processing_complete' || data.type === 'completed') {
        // Handle processing completion
        markProcessingComplete();
    }
    else {
        console.log('Unknown message type:', data.type);
    }
}

// Add AI message to chat
function addAIMessage(content) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ai-message';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    // Format message content (handle simple markdown)
    const formattedContent = formatMessage(content);
    messageContent.innerHTML = formattedContent;
    
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add system message to chat
function addSystemMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = message;
    
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add error message to chat
function addSystemErrorMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message error';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = `Error: ${message}`;
    
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Mark processing as complete
function markProcessingComplete() {
    const statusIndicator = document.getElementById('status-indicator');
    const sendButton = document.getElementById('send-btn');
    const stopButton = document.getElementById('stop-btn');
    
    if (statusIndicator) statusIndicator.textContent = 'Processing completed';
    if (sendButton) sendButton.disabled = false;
    if (stopButton) stopButton.disabled = true;
}

// Format message (simple markdown handling)
function formatMessage(content) {
    if (!content) return '';
    
    // Escape HTML
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Handle code blocks
    formatted = formatted.replace(/\`\`\`([^\`]+)\`\`\`/g, '<pre><code>$1</code></pre>');
    
    // Handle inline code
    formatted = formatted.replace(/\`([^\`]+)\`/g, '<code>$1</code>');
    
    // Handle bold
    formatted = formatted.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    
    // Handle italic
    formatted = formatted.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
    
    // Handle line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

// Add thinking step (placeholder - can be customized later)
function addThinkingStep(step) {
    const thinkingSteps = document.getElementById('thinking-steps');
    if (!thinkingSteps) return;
    
    // Create step container
    const stepElement = document.createElement('div');
    stepElement.className = 'thinking-step';
    
    // Get step data
    const stepNumber = step.step_number || step.index || 0;
    const stepContent = step.content || step.thinking || step.text || '';
    const stepType = step.type || 'thinking';
    
    // Create step header with step number
    const stepHeader = document.createElement('div');
    stepHeader.className = 'step-header';
    stepHeader.innerHTML = `<span class="step-number">${stepNumber}</span>`;
    
    // Create step content
    const stepContentElement = document.createElement('div');
    stepContentElement.className = 'step-content';
    
    // Format content (handle simple markdown)
    const formattedContent = formatMessage(stepContent);
    stepContentElement.innerHTML = formattedContent;
    
    // Add content to step
    stepElement.appendChild(stepHeader);
    stepElement.appendChild(stepContentElement);
    
    // Add to thinking steps
    thinkingSteps.appendChild(stepElement);
    thinkingSteps.scrollTop = thinkingSteps.scrollHeight;
    
    // Switch to thinking tab if this is the first thinking step
    if (stepNumber === 1) {
        const thinkingTab = document.querySelector('.log-tab[data-target="thinking-logs"]');
        if (thinkingTab) thinkingTab.click();
    }
}

// Update terminal (placeholder - implement as needed)
function updateTerminal(data) {
    console.log('Terminal update:', data);
    // Implementation would depend on terminal UI structure
}

// Update system logs (placeholder - implement as needed)
function updateSystemLogs(logs) {
    console.log('System logs update:', logs);
    // Implementation would depend on logs UI structure
}

// Add generated file (placeholder - implement as needed)
function addGeneratedFile(file) {
    console.log('File generated:', file);
    // Implementation would depend on file viewer UI structure
} 