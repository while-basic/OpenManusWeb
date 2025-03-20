// Sith Web UI Main Script

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI components
    initLogTabs();
    initToggleButtons();
    initFileViewer();
    initTerminal();
    
    // Initialize chat interface - MOST IMPORTANT
    const sendButton = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');
    const stopButton = document.getElementById('stop-btn');
    
    if (sendButton && userInput) {
        console.log('Initializing chat interface...');
        // Direct event handler attachment
        sendButton.onclick = function() {
            const message = userInput.value.trim();
            if (message) {
                sendChatMessage(message);
            }
        };
        
        userInput.onkeydown = function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                const message = userInput.value.trim();
                if (message) {
                    sendChatMessage(message);
                }
            }
        };
        
        if (stopButton) {
            stopButton.onclick = stopProcessing;
            stopButton.disabled = true;
        }
    } else {
        console.error('Chat interface elements not found!');
    }
    
    // Load system logs
    loadSystemLogs();
    
    // Initialize websocket connection for real-time updates
    initWebSocket();
});

// Initialize tabs in logs dashboard
function initLogTabs() {
    const tabs = document.querySelectorAll('.log-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Deactivate all tabs and panels
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.log-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            
            // Activate clicked tab and its panel
            tab.classList.add('active');
            const targetPanel = document.getElementById(tab.dataset.target);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }
        });
    });
}

// Initialize expand/collapse functionality for log panels
function initToggleButtons() {
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const panelId = btn.dataset.panel;
            const panel = document.getElementById(panelId);
            if (panel) {
                panel.classList.toggle('collapsed');
                btn.textContent = panel.classList.contains('collapsed') ? '⇓' : '⇕';
            }
        });
    });
    
    // Add clear buttons functionality
    document.getElementById('clear-logs')?.addEventListener('click', () => {
        document.getElementById('logs-content').innerHTML = '';
    });
    
    document.getElementById('clear-terminal')?.addEventListener('click', () => {
        document.getElementById('terminal-output').innerHTML = '';
    });
    
    document.getElementById('clear-thinking')?.addEventListener('click', () => {
        document.getElementById('thinking-steps').innerHTML = '';
    });
}

// Initialize file viewer functionality
function initFileViewer() {
    const fileViewer = document.getElementById('file-viewer');
    const closeButton = document.getElementById('close-file-viewer');
    
    if (fileViewer && closeButton) {
        closeButton.addEventListener('click', () => {
            fileViewer.classList.remove('active');
        });
        
        // Close on click outside the content area
        fileViewer.addEventListener('click', (e) => {
            if (e.target === fileViewer) {
                fileViewer.classList.remove('active');
            }
        });
    }
}

// Initialize terminal functionality
function initTerminal() {
    const terminalInput = document.getElementById('terminal-input');
    const runButton = document.getElementById('run-command');
    const interruptButton = document.getElementById('interrupt-command');
    const terminalOutput = document.getElementById('terminal-output');
    
    if (terminalInput && runButton && terminalOutput) {
        let commandId = null;
        let isCommandRunning = false;
        
        // Run command function
        const runCommand = async () => {
            const command = terminalInput.value.trim();
            
            if (!command && !isCommandRunning) {
                return;
            }
            
            // Add command to output
            if (command) {
                appendToTerminal(`$ ${command}`, 'command');
                terminalInput.value = '';
            }
            
            try {
                if (isCommandRunning) {
                    // Send input to running command
                    if (command === 'ctrl+c') {
                        await interruptCommand();
                        return;
                    }
                    
                    const response = await fetch('/api/terminal/input', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            command_id: commandId,
                            input: command
                        }),
                    });
                    
                    if (!response.ok) {
                        throw new Error(`API error: ${response.status}`);
                    }
                } else {
                    // Start new command
                    isCommandRunning = true;
                    runButton.disabled = true;
                    interruptButton.disabled = false;
                    
                    const response = await fetch('/api/terminal/execute', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            command: command
                        }),
                    });
                    
                    if (!response.ok) {
                        throw new Error(`API error: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    commandId = data.command_id;
                    
                    // Handle immediate result if available
                    if (data.output) {
                        appendToTerminal(data.output, 'result');
                    }
                    
                    if (data.error) {
                        appendToTerminal(data.error, 'error');
                    }
                    
                    // If command is completed
                    if (data.status === 'completed') {
                        commandComplete();
                    } else {
                        // Command is still running or interactive
                        appendToTerminal('Command running...', 'info');
                    }
                }
            } catch (error) {
                console.error('Terminal error:', error);
                appendToTerminal(`Error: ${error.message}`, 'error');
                commandComplete();
            }
        };
        
        // Command complete function
        const commandComplete = () => {
            isCommandRunning = false;
            commandId = null;
            runButton.disabled = false;
            interruptButton.disabled = true;
        };
        
        // Interrupt command function
        const interruptCommand = async () => {
            if (!isCommandRunning || !commandId) {
                return;
            }
            
            try {
                const response = await fetch('/api/terminal/interrupt', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        command_id: commandId
                    }),
                });
                
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                
                appendToTerminal('^C', 'command');
                commandComplete();
            } catch (error) {
                console.error('Error interrupting command:', error);
                appendToTerminal(`Error: ${error.message}`, 'error');
            }
        };
        
        // Append to terminal function
        const appendToTerminal = (text, type) => {
            const outputElement = document.createElement('div');
            outputElement.className = type;
            outputElement.textContent = text;
            
            terminalOutput.appendChild(outputElement);
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        };
        
        // Bind events
        runButton.addEventListener('click', runCommand);
        
        terminalInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                runCommand();
            }
        });
        
        interruptButton.addEventListener('click', interruptCommand);
        
        // Initialize state
        interruptButton.disabled = true;
    }
}

// Load system logs
async function loadSystemLogs() {
    try {
        const response = await fetch('/api/logs');
        const logs = await response.json();
        
        const logsContent = document.getElementById('logs-content');
        if (!logsContent) return;
        
        logsContent.innerHTML = '';
        
        if (!logs.logs || logs.logs.length === 0) {
            logsContent.innerHTML = '<div class="empty-message">No logs available</div>';
            return;
        }
        
        logs.logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <div class="log-entry-header">
                    <span class="log-name">${log.name}</span>
                    <span class="log-date">${new Date(log.modified * 1000).toLocaleString()}</span>
                </div>
                <div class="log-entry-details">
                    <span class="log-size">${(log.size/1024).toFixed(2)} KB</span>
                    <div class="log-actions">
                        <button class="view-log-btn" data-log="${log.name}">View Content</button>
                        <button class="view-status-btn" data-log="${log.name}">View Status</button>
                    </div>
                </div>
            `;
            logsContent.appendChild(logEntry);
        });
        
        // Add view log content button events
        document.querySelectorAll('.view-log-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const logName = e.target.getAttribute('data-log');
                loadLogContent(logName);
            });
        });
        
        // Add view execution status button events
        document.querySelectorAll('.view-status-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const logName = e.target.getAttribute('data-log');
                loadLogExecutionStatus(logName);
                
                // Switch to execution logs tab
                document.querySelector('.log-tab[data-target="execution-logs"]').click();
            });
        });
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

// Load log content
async function loadLogContent(logName) {
    try {
        const response = await fetch(`/api/logs/${logName}`);
        const logData = await response.json();
        
        // Display log content in terminal output area
        const terminalOutput = document.getElementById('terminal-output');
        if (terminalOutput) {
            terminalOutput.innerHTML = '';
            const logOutput = document.createElement('div');
            logOutput.className = 'result';
            logOutput.innerHTML = `<pre>${logData.content}</pre>`;
            terminalOutput.appendChild(logOutput);
            
            // Switch to terminal logs tab
            document.querySelector('.log-tab[data-target="terminal-logs"]').click();
        }
    } catch (error) {
        console.error('Error loading log content:', error);
    }
}

// Load log execution status
async function loadLogExecutionStatus(logName) {
    try {
        // Get parsed log information
        const response = await fetch(`/api/logs_parsed/${logName}`);
        const logInfo = await response.json();
        
        // Update status badge
        const statusBadge = document.getElementById('status-badge');
        statusBadge.textContent = getStatusText(logInfo.status);
        statusBadge.className = `status-badge status-${logInfo.status}`;
        
        // Update progress bar
        const progressBar = document.getElementById('execution-progress-bar');
        const progressText = document.getElementById('progress-text');
        const percentage = logInfo.progress_percentage || 0;
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${percentage}%`;
        
        // Update detailed information
        document.getElementById('plan-id').textContent = logInfo.plan_id || '-';
        document.getElementById('current-step').textContent = logInfo.current_step || '-';
        document.getElementById('completed-steps').textContent = logInfo.completed_steps || '0';
        document.getElementById('total-steps').textContent = logInfo.total_steps || '0';
        
        // Update steps list
        const stepsList = document.getElementById('steps-list');
        stepsList.innerHTML = '';
        
        if (logInfo.steps && logInfo.steps.length > 0) {
            logInfo.steps.forEach((step, index) => {
                const status = logInfo.step_statuses && logInfo.step_statuses[index]
                    ? logInfo.step_statuses[index]
                    : 'not_started';
                
                const stepItem = document.createElement('div');
                stepItem.className = `step-item step-${status}`;
                
                let statusIcon = '⬜';
                if (status === 'completed') statusIcon = '✅';
                else if (status === 'in_progress') statusIcon = '🔄';
                else if (status === 'blocked') statusIcon = '⚠️';
                
                stepItem.innerHTML = `
                    <span class="step-status">${statusIcon}</span>
                    <span class="step-number">${index + 1}.</span>
                    <span class="step-text">${step}</span>
                `;
                
                stepsList.appendChild(stepItem);
            });
        } else {
            stepsList.innerHTML = '<div class="no-steps">No steps information</div>';
        }
        
        // Update tools list
        const toolsList = document.getElementById('tools-list');
        toolsList.innerHTML = '';
        
        if (logInfo.tool_executions && logInfo.tool_executions.length > 0) {
            logInfo.tool_executions.forEach(tool => {
                const toolItem = document.createElement('div');
                toolItem.className = 'tool-item';
                
                if (tool.tool) {
                    toolItem.innerHTML = `
                        <span class="tool-icon">🔧</span>
                        <span class="tool-name">${tool.tool}</span>
                    `;
                } else if (tool.action) {
                    toolItem.innerHTML = `
                        <span class="tool-icon">🔄</span>
                        <span class="tool-action">${tool.action}</span>
                    `;
                }
                
                toolsList.appendChild(toolItem);
            });
        } else {
            toolsList.innerHTML = '<div class="no-tools">No tool usage records</div>';
        }
        
        // Update errors list
        const errorsList = document.getElementById('errors-list');
        errorsList.innerHTML = '';
        document.getElementById('errors-count').textContent = logInfo.errors ? logInfo.errors.length : '0';
        
        if (logInfo.errors && logInfo.errors.length > 0) {
            logInfo.errors.forEach(error => {
                const errorItem = document.createElement('div');
                errorItem.className = 'error-item';
                errorItem.innerHTML = `
                    <span class="error-icon">❌</span>
                    <span class="error-message">${error.message}</span>
                `;
                errorsList.appendChild(errorItem);
            });
        } else {
            errorsList.innerHTML = '<div class="no-errors">No errors</div>';
        }
        
        // Update warnings list
        const warningsList = document.getElementById('warnings-list');
        warningsList.innerHTML = '';
        document.getElementById('warnings-count').textContent = logInfo.warnings ? logInfo.warnings.length : '0';
        
        if (logInfo.warnings && logInfo.warnings.length > 0) {
            logInfo.warnings.forEach(warning => {
                const warningItem = document.createElement('div');
                warningItem.className = 'warning-item';
                warningItem.innerHTML = `
                    <span class="warning-icon">⚠️</span>
                    <span class="warning-message">${warning.message}</span>
                `;
                warningsList.appendChild(warningItem);
            });
        } else {
            warningsList.innerHTML = '<div class="no-warnings">No warnings</div>';
        }
    } catch (error) {
        console.error('Error loading execution status:', error);
    }
}

// Get status text
function getStatusText(status) {
    switch(status) {
        case 'completed': return 'Completed';
        case 'in_progress': return 'In Progress';
        case 'error': return 'Error';
        case 'stopped': return 'Stopped';
        default: return 'Unknown';
    }
}

// Initialize WebSocket connection for real-time updates
function initWebSocket() {
    // Get session ID from URL if available
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        console.log('No session ID found, WebSocket connection not established');
        return;
    }
    
    // Initialize global socket variable
    window.socket = null;
    window.reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 2000; // 2 seconds
    
    // Connect to WebSocket
    connect();
}

// Function to establish WebSocket connection
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
        updateStatus('Connected');
    };
    
    window.socket.onclose = function(event) {
        console.log('WebSocket connection closed', event);
        updateStatus('Disconnected');
        
        // Try to reconnect if not a normal closure
        if (event.code !== 1000) {
            setTimeout(connect, 2000);
        }
    };
    
    window.socket.onerror = function(error) {
        console.error('WebSocket error:', error);
        updateStatus('Connection Error');
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

// Function to update status indicator
function updateStatus(status) {
    const statusIndicator = document.getElementById('status-indicator');
    if (statusIndicator) {
        statusIndicator.textContent = status;
    }
}

// Function to handle WebSocket messages
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

// Function to add AI message to chat
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

// Function to format message (handle simple markdown)
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

// Function to add thinking step
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
        document.querySelector('.log-tab[data-target="thinking-logs"]').click();
    }
}

// Function to add generated file
function addGeneratedFile(file) {
    const filesList = document.getElementById('files-list');
    if (!filesList) return;
    
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.dataset.path = file.path;
    
    // Determine file icon based on extension
    let icon = '📄';
    const ext = file.name.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext)) {
        icon = '��️';
    } else if (['mp3', 'wav', 'ogg'].includes(ext)) {
        icon = '🔊';
    } else if (['mp4', 'webm', 'mov'].includes(ext)) {
        icon = '🎬';
    } else if (['zip', 'tar', 'gz', 'rar'].includes(ext)) {
        icon = '📦';
    } else if (['pdf'].includes(ext)) {
        icon = '📰';
    } else if (['doc', 'docx', 'txt', 'md'].includes(ext)) {
        icon = '📝';
    } else if (['xls', 'xlsx', 'csv'].includes(ext)) {
        icon = '📊';
    } else if (['js', 'ts', 'py', 'java', 'c', 'cpp', 'php', 'html', 'css'].includes(ext)) {
        icon = '💻';
    }
    
    fileItem.innerHTML = `
        <div class="file-icon">${icon}</div>
        <div class="file-name">${file.name}</div>
        <div class="file-meta">${formatFileSize(file.size)}</div>
    `;
    
    fileItem.addEventListener('click', () => {
        viewFile(file.path);
    });
    
    filesList.appendChild(fileItem);
}

// Function to update terminal with new output
function updateTerminal(data) {
    const terminalOutput = document.getElementById('terminal-output');
    if (!terminalOutput) return;
    
    if (data.output) {
        const outputElement = document.createElement('div');
        outputElement.className = 'result';
        outputElement.textContent = data.output;
        terminalOutput.appendChild(outputElement);
    }
    
    if (data.error) {
        const errorElement = document.createElement('div');
        errorElement.className = 'error';
        errorElement.textContent = data.error;
        terminalOutput.appendChild(errorElement);
    }
    
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

// Function to update system logs
function updateSystemLogs(logs) {
    if (!logs || logs.length === 0) return;
    
    const logsContent = document.getElementById('logs-content');
    if (!logsContent) return;
    
    logs.forEach(logText => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-line';
        logEntry.textContent = logText;
        logsContent.appendChild(logEntry);
    });
    
    logsContent.scrollTop = logsContent.scrollHeight;
}

// Function to mark processing as complete
function markProcessingComplete() {
    const statusIndicator = document.getElementById('status-indicator');
    if (statusIndicator) {
        statusIndicator.textContent = 'Processing completed';
    }
    
    // Enable send button and disable stop button
    const sendButton = document.getElementById('send-btn');
    const stopButton = document.getElementById('stop-btn');
    
    if (sendButton) sendButton.disabled = false;
    if (stopButton) stopButton.disabled = true;
}

// Function to view file content
async function viewFile(filePath) {
    try {
        const response = await fetch(`/api/files/${encodeURIComponent(filePath)}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        const fileViewer = document.getElementById('file-viewer');
        const fileTitle = document.getElementById('file-viewer-title');
        const fileContent = document.getElementById('file-content');
        
        if (fileViewer && fileTitle && fileContent) {
            fileTitle.textContent = data.name;
            fileContent.textContent = data.content;
            fileViewer.classList.add('active');
        }
    } catch (error) {
        console.error('Error viewing file:', error);
    }
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Helper function to add system message
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

// Helper function to add system error message
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

// Function to send a chat message
async function sendChatMessage(message) {
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
            
            // Connect with the new session ID
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

// Function to stop processing
async function stopProcessing() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) return;
    
    try {
        const response = await fetch(`/api/chat/${sessionId}/stop`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) statusIndicator.textContent = 'Processing stopped';
        
        // Update UI state
        const sendButton = document.getElementById('send-btn');
        const stopButton = document.getElementById('stop-btn');
        if (sendButton) sendButton.disabled = false;
        if (stopButton) stopButton.disabled = true;
    } catch (error) {
        console.error('Error stopping processing:', error);
    }
} 