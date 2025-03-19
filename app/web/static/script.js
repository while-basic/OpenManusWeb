// OpenManus Web UI Main Script

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI components
    initLogTabs();
    initToggleButtons();
    initFileViewer();
    initTerminal();
    
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
    let socket = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 2000; // 2 seconds
    
    // Get session ID from URL if available
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) {
        console.log('No session ID found, WebSocket connection not established');
        return;
    }
    
    // Function to establish WebSocket connection
    const connect = () => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${sessionId}`;
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function() {
            console.log('WebSocket connection established');
            reconnectAttempts = 0;
            updateStatus('Connected');
        };
        
        socket.onclose = function(event) {
            console.log('WebSocket connection closed', event);
            updateStatus('Disconnected');
            
            // Try to reconnect if not a normal closure
            if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                updateStatus(`Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
                setTimeout(connect, reconnectDelay);
            }
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            updateStatus('Connection Error');
        };
        
        socket.onmessage = function(event) {
            handleWebSocketMessage(event.data);
        };
    };
    
    // Function to update connection status indicator
    const updateStatus = (status) => {
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            statusIndicator.textContent = status;
        }
    };
    
    // Function to handle incoming WebSocket messages
    const handleWebSocketMessage = (data) => {
        try {
            const message = JSON.parse(data);
            
            // Handle different message types
            switch (message.type) {
                case 'thinking_step':
                    addThinkingStep(message);
                    break;
                    
                case 'ai_message':
                    addAIMessage(message.content);
                    break;
                    
                case 'file_generated':
                    addGeneratedFile(message.file);
                    break;
                    
                case 'terminal_update':
                    updateTerminal(message);
                    break;
                    
                case 'system_logs':
                    updateSystemLogs(message.logs);
                    break;
                    
                case 'completed':
                    markProcessingComplete();
                    break;
                    
                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };
    
    // Function to add thinking step
    const addThinkingStep = (step) => {
        const thinkingSteps = document.getElementById('thinking-steps');
        if (!thinkingSteps) return;
        
        const stepElement = document.createElement('div');
        stepElement.className = 'thinking-step';
        
        // Create header with step number and timestamp
        const header = document.createElement('div');
        header.className = 'thinking-step-header';
        
        const stepNumber = document.createElement('div');
        stepNumber.className = 'thinking-step-number';
        stepNumber.textContent = `Step ${step.thought_number || ''}`;
        
        const timestamp = document.createElement('div');
        timestamp.className = 'thinking-step-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        
        header.appendChild(stepNumber);
        header.appendChild(timestamp);
        
        // Create content
        const content = document.createElement('div');
        content.className = 'thinking-step-content';
        
        if (step.thought_number && step.total_thoughts) {
            content.innerHTML = `<strong>Thought ${step.thought_number}/${step.total_thoughts}:</strong> ${step.content}`;
        } else {
            content.textContent = step.content;
        }
        
        // Assemble the step element
        stepElement.appendChild(header);
        stepElement.appendChild(content);
        
        thinkingSteps.appendChild(stepElement);
        thinkingSteps.scrollTop = thinkingSteps.scrollHeight;
        
        // Switch to thinking tab if this is the first step
        if (step.thought_number === 1) {
            document.querySelector('.log-tab[data-target="thinking-logs"]').click();
        }
    };
    
    // Function to add AI message to chat
    const addAIMessage = (content) => {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-message';
        
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        messageHeader.innerHTML = '<span class="avatar">🤖</span><span class="sender">OpenManus</span>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;
        
        messageDiv.appendChild(messageHeader);
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };
    
    // Function to add generated file
    const addGeneratedFile = (file) => {
        const filesList = document.getElementById('files-list');
        if (!filesList) return;
        
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.dataset.path = file.path;
        
        // Determine file icon based on extension
        let icon = '📄';
        const ext = file.name.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext)) {
            icon = '🖼️';
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
    };
    
    // Function to update terminal with new output
    const updateTerminal = (data) => {
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
    };
    
    // Function to update system logs
    const updateSystemLogs = (logs) => {
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
    };
    
    // Function to mark processing as complete
    const markProcessingComplete = () => {
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            statusIndicator.textContent = 'Processing completed';
        }
        
        // Enable send button and disable stop button
        const sendButton = document.getElementById('send-btn');
        const stopButton = document.getElementById('stop-btn');
        
        if (sendButton) sendButton.disabled = false;
        if (stopButton) stopButton.disabled = true;
    };
    
    // Function to view file content
    const viewFile = async (filePath) => {
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
    };
    
    // Helper function to format file size
    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };
    
    // Start the WebSocket connection
    connect();
    
    // Handle send button click
    const sendButton = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');
    const stopButton = document.getElementById('stop-btn');
    const chatMessages = document.getElementById('chat-messages');
    
    if (sendButton && userInput && chatMessages) {
        sendButton.addEventListener('click', () => {
            const message = userInput.value.trim();
            if (!message) return;
            
            // Add user message to chat
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user-message';
            
            const messageHeader = document.createElement('div');
            messageHeader.className = 'message-header';
            messageHeader.innerHTML = '<span class="avatar">👤</span><span class="sender">You</span>';
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            messageContent.textContent = message;
            
            messageDiv.appendChild(messageHeader);
            messageDiv.appendChild(messageContent);
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Clear input
            userInput.value = '';
            
            // Disable send button and enable stop button
            sendButton.disabled = true;
            if (stopButton) stopButton.disabled = false;
            
            // Update status
            updateStatus('Processing...');
            
            // Send message to server
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: message }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Set session ID in URL without reloading page
                if (data.session_id && data.session_id !== sessionId) {
                    const url = new URL(window.location);
                    url.searchParams.set('session_id', data.session_id);
                    window.history.pushState({}, '', url);
                    
                    // Reconnect WebSocket with new session ID
                    if (socket) {
                        socket.close();
                        setTimeout(connect, 500);
                    }
                }
            })
            .catch(error => {
                console.error('Error sending message:', error);
                addSystemErrorMessage(error.message);
                updateStatus('Error');
                sendButton.disabled = false;
                if (stopButton) stopButton.disabled = true;
            });
        });
        
        // Handle enter key in input field
        userInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendButton.click();
            }
        });
        
        // Handle stop button
        if (stopButton) {
            stopButton.addEventListener('click', () => {
                if (!sessionId) return;
                
                fetch(`/api/chat/${sessionId}/stop`, {
                    method: 'POST',
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`API error: ${response.status}`);
                    }
                    updateStatus('Stopped');
                    sendButton.disabled = false;
                    stopButton.disabled = true;
                    addSystemMessage('Processing stopped by user');
                })
                .catch(error => {
                    console.error('Error stopping processing:', error);
                    addSystemErrorMessage(error.message);
                });
            });
            
            // Initially disable stop button
            stopButton.disabled = true;
        }
    }
    
    // Helper function to add system message
    function addSystemMessage(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        messageHeader.innerHTML = '<span class="avatar">ℹ️</span><span class="sender">System</span>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = message;
        
        messageDiv.appendChild(messageHeader);
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Helper function to add system error message
    function addSystemErrorMessage(message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message error-message';
        
        const messageHeader = document.createElement('div');
        messageHeader.className = 'message-header';
        messageHeader.innerHTML = '<span class="avatar">⚠️</span><span class="sender">Error</span>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = message;
        
        messageDiv.appendChild(messageHeader);
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
} 