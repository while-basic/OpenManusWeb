// SUPER EMERGENCY FIX - Direct global click handling for modern UI
(function() {
    console.log("🔴 SUPER EMERGENCY FIX LOADING for MODERN UI - v3");
    
    // Find elements in the modern UI
    function getSendButton() { 
        // Try different possible selectors for the send button
        return document.querySelector('button[aria-label="Send"]') || 
               document.querySelector('button:has(svg[data-icon="paper-plane"])') ||
               document.querySelector('button:has(svg)') ||
               document.querySelector('button:contains("Send")') ||
               document.querySelector('button.chat-send-btn') ||
               document.querySelector('[data-testid="send-button"]') ||
               document.querySelector('[class*="send"]') ||
               document.querySelector('[class*="send-button"]') ||
               document.querySelector('[aria-label*="send"]') ||
               document.querySelector('button:nth-child(1)');
    }
    
    function getUserInput() { 
        // Try different possible selectors for the text input
        return document.querySelector('textarea') || 
               document.querySelector('div[contenteditable="true"]') || 
               document.querySelector('input[type="text"]');
    }
    
    function getChatMessages() { 
        // Try different selectors for the chat container
        return document.querySelector('.conversation') || 
               document.querySelector('[class*="messages"]') || 
               document.querySelector('[class*="chat-content"]') ||
               document.querySelector('[class*="conversation"]');
    }
    
    // Add debug message directly to the page
    function addDebugMessage(text) {
        console.log('🛠️ DEBUG:', text);
        
        try {
            // Create a floating debug div if it doesn't exist
            let debugDiv = document.getElementById('emergency-debug-messages');
            if (!debugDiv) {
                debugDiv = document.createElement('div');
                debugDiv.id = 'emergency-debug-messages';
                debugDiv.style.position = 'fixed';
                debugDiv.style.bottom = '10px';
                debugDiv.style.right = '10px';
                debugDiv.style.width = '300px';
                debugDiv.style.maxHeight = '200px';
                debugDiv.style.overflowY = 'auto';
                debugDiv.style.backgroundColor = 'rgba(0,0,0,0.8)';
                debugDiv.style.color = '#ff5555';
                debugDiv.style.padding = '10px';
                debugDiv.style.borderRadius = '5px';
                debugDiv.style.fontFamily = 'monospace';
                debugDiv.style.fontSize = '12px';
                debugDiv.style.zIndex = '9999';
                document.body.appendChild(debugDiv);
            }
            
            // Add message
            const msgElem = document.createElement('div');
            msgElem.textContent = `${new Date().toISOString().split('T')[1].split('.')[0]} - ${text}`;
            msgElem.style.borderBottom = '1px solid #333';
            msgElem.style.paddingBottom = '4px';
            msgElem.style.marginBottom = '4px';
            debugDiv.appendChild(msgElem);
            debugDiv.scrollTop = debugDiv.scrollHeight;
        } catch (e) {
            console.error('Error adding debug message:', e);
        }
    }
    
    // The actual send function - works with both old and new UIs
    function sendChatMessage() {
        try {
            const userInput = getUserInput();
            const sendBtn = getSendButton();
            
            if (!userInput || !sendBtn) {
                console.error('Missing required elements for sending message');
                addDebugMessage('❌ Cannot find input or send button');
                return;
            }
            
            // Get message from input based on element type
            let message = '';
            if (userInput.tagName === 'TEXTAREA' || userInput.tagName === 'INPUT') {
                message = userInput.value.trim();
            } else if (userInput.getAttribute('contenteditable') === 'true') {
                message = userInput.textContent.trim();
            }
            
            if (!message) {
                addDebugMessage('❌ No message to send');
                return;
            }
            
            console.log('🚀 SUPER EMERGENCY SEND ACTIVATED: ', message);
            addDebugMessage('Sending message: ' + message);
            
            // Native click event - most reliable method
            sendBtn.click();
            
            // If that didn't work, try dispatching events
            const clickEvent = new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window
            });
            sendBtn.dispatchEvent(clickEvent);
            
            addDebugMessage('✅ Send button clicked!');
        } catch (err) {
            console.error('Error in sendChatMessage:', err);
            addDebugMessage('❌ Error: ' + err.message);
        }
    }
    
    // Create emergency buttons that will work with any UI
    function createEmergencyControls() {
        try {
            // Create container for our emergency controls
            const container = document.createElement('div');
            container.id = 'emergency-chat-controls';
            container.style.position = 'fixed';
            container.style.bottom = '10px';
            container.style.left = '10px';
            container.style.zIndex = '9999';
            container.style.display = 'flex';
            container.style.flexDirection = 'column';
            container.style.gap = '10px';
            
            // Create emergency send button
            const emergencySend = document.createElement('button');
            emergencySend.textContent = '🚨 EMERGENCY SEND';
            emergencySend.style.backgroundColor = '#ff3333';
            emergencySend.style.color = 'white';
            emergencySend.style.fontWeight = 'bold';
            emergencySend.style.padding = '10px 15px';
            emergencySend.style.border = 'none';
            emergencySend.style.borderRadius = '5px';
            emergencySend.style.cursor = 'pointer';
            
            // Add click handler
            emergencySend.addEventListener('click', function(e) {
                e.stopPropagation();
                e.preventDefault();
                sendChatMessage();
            });
            
            // Create debug button
            const debugButton = document.createElement('button');
            debugButton.textContent = '🛠️ Show UI Debug';
            debugButton.style.backgroundColor = '#333';
            debugButton.style.color = 'white';
            debugButton.style.padding = '8px 12px';
            debugButton.style.border = 'none';
            debugButton.style.borderRadius = '5px';
            debugButton.style.cursor = 'pointer';
            debugButton.style.fontSize = '12px';
            
            // Add click handler for debug button
            debugButton.addEventListener('click', function() {
                const sendBtn = getSendButton();
                const userInput = getUserInput();
                const chatMessages = getChatMessages();
                
                addDebugMessage(`Send button: ${sendBtn ? '✅ Found' : '❌ Not found'}`);
                addDebugMessage(`Input field: ${userInput ? '✅ Found' : '❌ Not found'}`);
                addDebugMessage(`Chat container: ${chatMessages ? '✅ Found' : '❌ Not found'}`);
                
                if (sendBtn) {
                    addDebugMessage(`Button tag: ${sendBtn.tagName}, classes: ${sendBtn.className}`);
                }
                if (userInput) {
                    addDebugMessage(`Input tag: ${userInput.tagName}, type: ${userInput.type || 'N/A'}`);
                }
            });
            
            // Add buttons to container
            container.appendChild(emergencySend);
            container.appendChild(debugButton);
            
            // Add container to page
            document.body.appendChild(container);
            
            addDebugMessage('Emergency controls added to page');
        } catch (e) {
            console.error('Error creating emergency controls:', e);
        }
    }
    
    // Global click handler for any element that looks like a send button
    document.addEventListener('click', function(e) {
        // Check if click was on something that looks like a send button
        if (e.target.tagName === 'BUTTON' || 
            e.target.closest('button') || 
            e.target.getAttribute('role') === 'button' ||
            e.target.closest('[role="button"]')) {
            
            const targetElem = e.target.tagName === 'BUTTON' ? 
                e.target : 
                (e.target.closest('button') || e.target.closest('[role="button"]'));
            
            // Check if it looks like a send button
            const buttonText = targetElem.textContent.toLowerCase();
            const buttonClasses = targetElem.className.toLowerCase();
            const isLikelySendButton = 
                buttonText.includes('send') ||
                buttonClasses.includes('send') ||
                targetElem.getAttribute('aria-label')?.toLowerCase().includes('send') ||
                targetElem.id.toLowerCase().includes('send');
            
            if (isLikelySendButton) {
                console.log('🎯 Potential send button click detected');
                
                // Don't preventDefault here - let the normal flow continue
                // Just log the action for debugging
                
                const userInput = getUserInput();
                if (userInput) {
                    let message = '';
                    if (userInput.tagName === 'TEXTAREA' || userInput.tagName === 'INPUT') {
                        message = userInput.value.trim();
                    } else if (userInput.getAttribute('contenteditable') === 'true') {
                        message = userInput.textContent.trim();
                    }
                    
                    if (message) {
                        addDebugMessage(`Regular send button clicked with message: ${message}`);
                    }
                }
            }
        }
    }, true);
    
    // Global key handler for Enter key in text inputs
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            const activeElement = document.activeElement;
            const userInput = getUserInput();
            
            if (activeElement === userInput || activeElement.closest('div[contenteditable="true"]')) {
                console.log('🎯 Enter key detected in input field');
                
                // Only prevent default for contenteditable (allow normal behavior for textarea)
                if (activeElement.getAttribute('contenteditable') === 'true') {
                    e.preventDefault();
                    addDebugMessage('Enter key pressed in contenteditable input');
                    sendChatMessage();
                }
            }
        }
    }, true);
    
    // Initialize with delay to ensure DOM is ready
    function init() {
        addDebugMessage('SUPER EMERGENCY FIX v3 ACTIVATED');
        createEmergencyControls();
        
        // Debug UI elements
        setTimeout(function() {
            const sendBtn = getSendButton();
            const userInput = getUserInput();
            const chatMessages = getChatMessages();
            
            addDebugMessage(`Send button: ${sendBtn ? '✅ Found' : '❌ Not found'}`);
            addDebugMessage(`Input field: ${userInput ? '✅ Found' : '❌ Not found'}`);
            addDebugMessage(`Chat container: ${chatMessages ? '✅ Found' : '❌ Not found'}`);
        }, 1000);
    }
    
    // Run on load
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(init, 100);
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(init, 500);
        });
    }
    
    // Also try after a longer delay in case of slow loading
    setTimeout(init, 2000);
})(); 