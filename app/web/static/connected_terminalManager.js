// connected_terminalManager.js - Terminal command execution and interaction manager

import { t } from '/static/i18n.js';

export class TerminalManager {
    constructor() {
        this.terminal = null;
        this.terminalInput = null;
        this.terminalOutput = null;
        this.runButton = null;
        this.interruptButton = null;
        this.clearButton = null;
        this.isCommandRunning = false;
        this.commandId = null;
        this.autoScroll = true;
    }

    init() {
        // Get DOM elements
        this.terminal = document.getElementById('terminal-section');
        this.terminalInput = document.getElementById('terminal-input');
        this.terminalOutput = document.getElementById('terminal-output');
        this.runButton = document.getElementById('run-command');
        this.interruptButton = document.getElementById('interrupt-command');
        this.clearButton = document.getElementById('clear-terminal');

        // Initialize state
        this.interruptButton.disabled = true;

        // Bind events
        this.bindEvents();
    }

    bindEvents() {
        // Run command on button click
        this.runButton.addEventListener('click', () => {
            this.executeCommand();
        });

        // Run command on Enter key
        this.terminalInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.executeCommand();
            }
        });

        // Interrupt command
        this.interruptButton.addEventListener('click', () => {
            this.interruptCommand();
        });

        // Clear terminal
        this.clearButton.addEventListener('click', () => {
            this.clearTerminal();
        });
    }

    async executeCommand() {
        const command = this.terminalInput.value.trim();
        
        if (!command && !this.isCommandRunning) {
            return;
        }

        // Add command to output
        if (command) {
            this.appendToOutput(`$ ${command}`, 'command');
            this.terminalInput.value = '';
        }

        try {
            // If a command is already running, this is input to that command
            if (this.isCommandRunning) {
                if (command === 'ctrl+c') {
                    await this.interruptCommand();
                    return;
                }
                
                // Send input to running command
                const response = await fetch('/api/terminal/input', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        command_id: this.commandId,
                        input: command
                    }),
                });

                if (!response.ok) {
                    throw new Error(t('api_error', { status: response.status }));
                }
            } else {
                // Start new command
                this.isCommandRunning = true;
                this.runButton.disabled = true;
                this.interruptButton.disabled = false;

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
                    throw new Error(t('api_error', { status: response.status }));
                }

                const data = await response.json();
                this.commandId = data.command_id;

                // Handle immediate result if available
                if (data.output) {
                    this.appendToOutput(data.output, 'result');
                }
                
                if (data.error) {
                    this.appendToOutput(data.error, 'error');
                }

                // If command is completed
                if (data.status === 'completed') {
                    this.commandComplete();
                } else {
                    // Command is still running or interactive
                    this.appendToOutput(t('command_running'), 'info');
                }
            }
        } catch (error) {
            console.error('Terminal error:', error);
            this.appendToOutput(t('command_error', { message: error.message }), 'error');
            this.commandComplete();
        }
    }

    async interruptCommand() {
        if (!this.isCommandRunning || !this.commandId) {
            return;
        }

        try {
            const response = await fetch('/api/terminal/interrupt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    command_id: this.commandId
                }),
            });

            if (!response.ok) {
                throw new Error(t('api_error', { status: response.status }));
            }

            this.appendToOutput('^C', 'command');
            this.commandComplete();
        } catch (error) {
            console.error('Error interrupting command:', error);
            this.appendToOutput(t('command_error', { message: error.message }), 'error');
        }
    }

    commandComplete() {
        this.isCommandRunning = false;
        this.commandId = null;
        this.runButton.disabled = false;
        this.interruptButton.disabled = true;
    }

    appendToOutput(text, type) {
        const outputElement = document.createElement('div');
        outputElement.className = type;
        outputElement.textContent = text;
        
        this.terminalOutput.appendChild(outputElement);
        
        if (this.autoScroll) {
            this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
        }
    }

    clearTerminal() {
        this.terminalOutput.innerHTML = '';
    }

    // Add this method to be called from the main app class for WebSocket updates
    handleTerminalUpdate(data) {
        if (data.command_id !== this.commandId) {
            return;
        }

        if (data.output) {
            this.appendToOutput(data.output, 'result');
        }
        
        if (data.error) {
            this.appendToOutput(data.error, 'error');
        }

        if (data.status === 'completed') {
            this.appendToOutput(t('command_completed'), 'info');
            this.commandComplete();
        }
    }
} 