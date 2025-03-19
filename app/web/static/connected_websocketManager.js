// connected_websocketManager.js - Handles WebSocket connections and messages

export class WebSocketManager {
    constructor(messageHandler, errorHandler) {
        this.socket = null;
        this.messageHandler = messageHandler;
        this.errorHandler = errorHandler;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Initial reconnect delay (1 second)
        this.sessionId = null;
    }

    // Connect to WebSocket
    connect(sessionId) {
        // Save session ID
        this.sessionId = sessionId;

        // Close existing connection if any
        if (this.socket) {
            this.socket.close();
        }

        // Reset reconnect attempt counter
        this.reconnectAttempts = 0;

        // Create WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);

        this.socket = new WebSocket(wsUrl);

        // Set event handlers
        this.socket.onopen = this.handleOpen.bind(this);
        this.socket.onmessage = this.handleMessage.bind(this);
        this.socket.onclose = this.handleClose.bind(this);
        this.socket.onerror = this.handleError.bind(this);
    }

    // Handle connection open
    handleOpen(event) {
        console.log('WebSocket connection established');
        document.getElementById('status-indicator').textContent = 'Connected to server...';
        // Reset reconnect attempt counter
        this.reconnectAttempts = 0;
    }

    // Handle received messages
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received WebSocket message:', data);

            // Call message handler callback
            if (this.messageHandler) {
                this.messageHandler(data);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            
            // Call error handler callback
            if (this.errorHandler) {
                this.errorHandler({
                    type: 'parse_error',
                    message: `Failed to parse WebSocket message: ${error.message}`,
                    rawData: event.data
                });
            }
        }
    }

    // Handle connection close
    handleClose(event) {
        // Normal closure (1000) or going away (1001)
        const isNormalClosure = event.code === 1000 || event.code === 1001;
        
        console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
        
        if (!isNormalClosure && this.errorHandler) {
            // Not a normal closure, report as error
            this.errorHandler({
                type: 'connection_closed',
                code: event.code,
                reason: event.reason || 'Connection closed unexpectedly',
                message: `Connection closed: ${event.reason || 'Server disconnected'} (Code: ${event.code})`
            });
        }

        // Attempt to reconnect for unexpected closures
        if (!isNormalClosure) {
            this.attemptReconnect();
        }
    }

    // Handle connection error
    handleError(error) {
        console.error('WebSocket error:', error);
        
        // Call error handler callback
        if (this.errorHandler) {
            this.errorHandler({
                type: 'connection_error',
                message: 'Connection error with server',
                originalError: error
            });
        }
    }

    // Attempt to reconnect
    attemptReconnect() {
        if (!this.sessionId) {
            console.log('No session ID, cannot reconnect');
            return;
        }

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Maximum reconnection attempts reached, giving up');
            document.getElementById('status-indicator').textContent = 'Connection lost, please refresh the page';
            
            // Call error handler with final error
            if (this.errorHandler) {
                this.errorHandler({
                    type: 'reconnect_failed',
                    message: 'Failed to reconnect after multiple attempts',
                    attempts: this.reconnectAttempts
                });
            }
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff

        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}), delay ${delay}ms`);
        document.getElementById('status-indicator').textContent = `Connection lost, attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`;

        setTimeout(() => {
            if (this.sessionId) {
                this.connect(this.sessionId);
            }
        }, delay);
    }

    // Send message
    send(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not connected, cannot send message');
            
            // Call error handler
            if (this.errorHandler) {
                this.errorHandler({
                    type: 'send_error',
                    message: 'Cannot send message: WebSocket not connected',
                    attemptedMessage: message
                });
            }
        }
    }

    // Close connection
    close() {
        if (this.socket) {
            this.socket.close(1000, "Client closing connection");
            this.socket = null;
        }
    }
}
