// connected_workspaceManager.js - Workspace files display manager

import { t } from '/static/i18n.js';

export class WorkspaceManager {
    constructor(fileClickCallback) {
        this.workspaceContainer = document.getElementById('workspace-files');
        this.refreshCountdownElement = document.getElementById('refresh-countdown');
        this.fileClickCallback = fileClickCallback;
        this.workspaces = [];
        this.refreshTimer = null;
        this.countdownValue = 5;
    }

    // Initialize workspace manager
    init() {
        // Set auto refresh timer
        this.startRefreshTimer();
    }

    // Update workspace list
    updateWorkspaces(workspaces) {
        if (!Array.isArray(workspaces)) return;

        this.workspaces = workspaces;
        this.renderWorkspaces();
    }

    // Render workspace list
    renderWorkspaces() {
        // Clear container
        this.workspaceContainer.innerHTML = '';

        // If no workspaces, show message
        if (this.workspaces.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'empty-workspace';
            emptyDiv.textContent = t('no_workspace_files');
            this.workspaceContainer.appendChild(emptyDiv);
            return;
        }

        // Render each workspace
        this.workspaces.forEach(workspace => {
            // Create workspace item
            const workspaceItem = this.createWorkspaceItem(workspace);
            this.workspaceContainer.appendChild(workspaceItem);

            // Render files under workspace
            if (workspace.files && workspace.files.length > 0) {
                workspace.files.forEach(file => {
                    const fileItem = this.createFileItem(file);
                    this.workspaceContainer.appendChild(fileItem);
                });
            }
        });
    }

    // Create workspace item
    createWorkspaceItem(workspace) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'workspace-item';

        // Create icon
        const iconDiv = document.createElement('div');
        iconDiv.className = 'workspace-icon';
        iconDiv.textContent = '📁';
        itemDiv.appendChild(iconDiv);

        // Create details container
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'workspace-details';

        // Create workspace name
        const nameDiv = document.createElement('div');
        nameDiv.className = 'workspace-name';
        nameDiv.textContent = workspace.name;
        detailsDiv.appendChild(nameDiv);

        // Create modification time
        const dateDiv = document.createElement('div');
        dateDiv.className = 'workspace-date';
        dateDiv.textContent = this.formatDate(workspace.modified);
        detailsDiv.appendChild(dateDiv);

        itemDiv.appendChild(detailsDiv);
        return itemDiv;
    }

    // Create file item
    createFileItem(file) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'file-item';
        itemDiv.dataset.path = file.path;

        // Create icon
        const iconDiv = document.createElement('div');
        iconDiv.className = 'file-icon';
        iconDiv.textContent = this.getFileIcon(file.type);
        itemDiv.appendChild(iconDiv);

        // Create details container
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'file-details';

        // Create file name
        const nameDiv = document.createElement('div');
        nameDiv.className = 'file-name';
        nameDiv.textContent = file.name;
        detailsDiv.appendChild(nameDiv);

        // Create file metadata
        const metaDiv = document.createElement('div');
        metaDiv.className = 'file-meta';
        metaDiv.textContent = `${this.formatFileSize(file.size)} · ${this.formatDate(file.modified)}`;
        detailsDiv.appendChild(metaDiv);

        itemDiv.appendChild(detailsDiv);

        // Bind click event
        itemDiv.addEventListener('click', () => {
            // Remove selected state from other files
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });

            // Add selected state
            itemDiv.classList.add('selected');

            // Call callback function
            if (this.fileClickCallback) {
                this.fileClickCallback(file);
            }
        });

        return itemDiv;
    }

    // Get file icon
    getFileIcon(fileType) {
        switch (fileType) {
            case 'txt':
                return '📄';
            case 'md':
                return '📝';
            case 'html':
                return '🌐';
            case 'css':
                return '🎨';
            case 'js':
                return '📜';
            case 'py':
                return '🐍';
            case 'json':
                return '📊';
            default:
                return '📄';
        }
    }

    // Format file size
    formatFileSize(size) {
        if (size < 1024) {
            return `${size} B`;
        } else if (size < 1024 * 1024) {
            return `${(size / 1024).toFixed(0)} KB`;
        } else {
            return `${(size / (1024 * 1024)).toFixed(1)} MB`;
        }
    }

    // Format date
    formatDate(timestamp) {
        if (!timestamp) return '';

        const date = new Date(timestamp * 1000);
        return date.toLocaleString();
    }

    // Start auto refresh timer
    startRefreshTimer() {
        // Clear existing timer
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // Reset countdown value
        this.countdownValue = 5;
        this.refreshCountdownElement.textContent = t('refresh_countdown', { seconds: this.countdownValue });

        // Set new timer, update every 1 second
        this.refreshTimer = setInterval(() => {
            this.countdownValue--;

            if (this.countdownValue > 0) {
                this.refreshCountdownElement.textContent = t('refresh_countdown', { seconds: this.countdownValue });
            } else {
                this.refreshCountdownElement.textContent = t('refresh');
                // Trigger refresh
                this.refreshWorkspaces();
                // Reset countdown
                this.countdownValue = 5;
                this.refreshCountdownElement.textContent = t('refresh_countdown', { seconds: this.countdownValue });
            }
        }, 1000);
    }

    // Refresh workspace files
    async refreshWorkspaces() {
        try {
            const response = await fetch('/api/files');
            if (!response.ok) {
                throw new Error(t('api_error', { status: response.status }));
            }

            const data = await response.json();
            this.updateWorkspaces(data.workspaces);

            console.log('Refreshed file list');

        } catch (error) {
            console.error(t('load_workspace_error', { message: error.message }));
        }
    }
}
