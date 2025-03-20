// simple_send.js - Direct port of the working inline script from index.html
(function() {
    console.log('🟢 Simple Send Module Loading - Direct Port of Working Code');
    
    // Function to create and add a button that will work with any UI
    function addSimpleSendButton() {
        try {
            // Create container
            const container = document.createElement('div');
            container.style.position = 'fixed';
            container.style.bottom = '20px';
            container.style.left = '20px';
            container.style.zIndex = '9999';
            container.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
            container.style.padding = '15px';
            container.style.borderRadius = '8px';
            container.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.3)';
            container.style.display = 'flex';
            container.style.flexDirection = 'column';
            container.style.gap = '10px';
            container.style.maxWidth = '400px';
            
            // Add title
            const title = document.createElement('div');
            title.textContent = 'Original Working Send';
            title.style.color = 'white';
            title.style.fontWeight = 'bold';
            title.style.marginBottom = '10px';
            title.style.borderBottom = '1px solid #555';
            title.style.paddingBottom = '5px';
            container.appendChild(title);
            
            // Create textarea for input
            const textarea = document.createElement('textarea');
            textarea.placeholder = 'Enter message here...';
            textarea.style.width = '100%';
            textarea.style.padding = '10px';
            textarea.style.borderRadius = '4px';
            textarea.style.border = 'none';
            textarea.style.resize = 'vertical';
            textarea.style.minHeight = '60px';
            textarea.style.maxHeight = '200px';
            textarea.style.marginBottom = '10px';
            textarea.style.backgroundColor = '#333';
            textarea.style.color = 'white';
            container.appendChild(textarea);
            
            // Button container
            const buttonContainer = document.createElement('div');
            buttonContainer.style.display = 'flex';
            buttonContainer.style.gap = '8px';
            
            // Create send button
            const sendButton = document.createElement('button');
            sendButton.textContent = 'Send Message';
            sendButton.style.backgroundColor = '#4CAF50';
            sendButton.style.color = 'white';
            sendButton.style.border = 'none';
            sendButton.style.borderRadius = '4px';
            sendButton.style.padding = '8px 16px';
            sendButton.style.cursor = 'pointer';
            sendButton.style.flex = '1';
            buttonContainer.appendChild(sendButton);
            
            // Create clear button
            const clearButton = document.createElement('button');
            clearButton.textContent = 'Clear';
            clearButton.style.backgroundColor = '#555';
            clearButton.style.color = 'white';
            clearButton.style.border = 'none';
            clearButton.style.borderRadius = '4px';
            clearButton.style.padding = '8px 16px';
            clearButton.style.cursor = 'pointer';
            buttonContainer.appendChild(clearButton);
            
            container.appendChild(buttonContainer);
            
            // Create output area
            const outputArea = document.createElement('div');
            outputArea.style.backgroundColor = '#222';
            outputArea.style.color = '#ddd';
            outputArea.style.borderRadius = '4px';
            outputArea.style.padding = '10px';
            outputArea.style.marginTop = '10px';
            outputArea.style.maxHeight = '200px';
            outputArea.style.overflowY = 'auto';
            outputArea.style.fontFamily = 'monospace';
            outputArea.style.fontSize = '12px';
            outputArea.textContent = 'Status: Ready';
            container.appendChild(outputArea);
            
            // Add to page
            document.body.appendChild(container);
            
            // Direct port of the working code's event handler
            sendButton.onclick = function() {
                const message = textarea.value.trim();
                if (message) {
                    // Update UI
                    outputArea.textContent = 'Sending: ' + message;
                    sendButton.disabled = true;
                    
                    // Directly send to server with the same endpoint and format as the original code
                    fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ prompt: message })
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Success:', data);
                        outputArea.textContent = 'Response received with session ID: ' + data.session_id;
                        sendButton.disabled = false;
                        textarea.value = '';
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        outputArea.textContent = 'Error: ' + error.message;
                        sendButton.disabled = false;
                    });
                }
            };
            
            // Handle Enter key
            textarea.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendButton.click();
                }
            });
            
            // Clear button
            clearButton.onclick = function() {
                textarea.value = '';
                outputArea.textContent = 'Cleared';
            };
            
            console.log('🟢 Simple Send Panel Added');
        } catch (e) {
            console.error('Error creating simple send panel:', e);
        }
    }
    
    // Initialize with delay to ensure DOM is ready
    function init() {
        setTimeout(addSimpleSendButton, 500);
    }
    
    // Run on load
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        init();
    } else {
        document.addEventListener('DOMContentLoaded', init);
    }
})(); 