// static/js/app.js - Updated with AD Credential Support
class UserDeprovisioningApp {
    constructor() {
        this.isProcessing = false;
        this.results = [];
        this.currentPassword = null;
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.validateForm();
        this.addInitialLogEntry();
    }
    
    setupEventListeners() {
        const emailInput = document.getElementById('userEmail');
        emailInput?.addEventListener('input', () => this.validateForm());
        
        const adUsername = document.getElementById('adUsername');
        const adPassword = document.getElementById('adPassword');
        adUsername?.addEventListener('input', () => this.validateForm());
        adPassword?.addEventListener('input', () => this.validateForm());
        
        const confirmInput = document.getElementById('confirmationInput');
        confirmInput?.addEventListener('input', () => this.validateConfirmation());
        
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        // Clear password field on page refresh for security
        if (adPassword) {
            adPassword.value = '';
        }
    }
    
    handleKeyboard(event) {
        if (event.key === 'Escape') {
            this.closeConfirmation();
        }
        
        if (event.ctrlKey && event.key === 'Enter') {
            if (!this.isProcessing && this.validateForm()) {
                this.startDeprovisioning();
            }
        }
        
        if (event.ctrlKey && event.key === 't') {
            event.preventDefault();
            this.testConnections();
        }
    }
    
    addInitialLogEntry() {
        const timestamp = new Date().toLocaleTimeString();
        this.addLogEntry('System initialized with user authentication. Enter AD credentials to begin.', 'info', timestamp);
    }
    
    validateForm() {
        const userEmail = document.getElementById('userEmail')?.value.trim();
        const adUsername = document.getElementById('adUsername')?.value.trim();
        const adPassword = document.getElementById('adPassword')?.value.trim();
        const deprovisionBtn = document.getElementById('deprovisionBtn');
        const testBtn = document.getElementById('testBtn');
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const isEmailValid = userEmail && emailRegex.test(userEmail);
        const areAdCredsValid = adUsername && adPassword && adUsername.length > 0 && adPassword.length > 0;
        
        // Update visual feedback
        const emailInput = document.getElementById('userEmail');
        const usernameInput = document.getElementById('adUsername');
        const passwordInput = document.getElementById('adPassword');
        
        if (emailInput) {
            emailInput.style.borderColor = isEmailValid ? '#27ae60' : 
                (userEmail ? '#e74c3c' : '#e0e6ed');
        }
        
        if (usernameInput) {
            usernameInput.style.borderColor = adUsername ? '#27ae60' : '#e0e6ed';
        }
        
        if (passwordInput) {
            passwordInput.style.borderColor = adPassword ? '#27ae60' : '#e0e6ed';
        }
        
        // Enable/disable buttons
        const isFormValid = isEmailValid && areAdCredsValid;
        
        if (deprovisionBtn) {
            deprovisionBtn.disabled = !isFormValid || this.isProcessing;
        }
        
        if (testBtn) {
            testBtn.disabled = !areAdCredsValid || this.isProcessing;
        }
        
        return isFormValid;
    }
    
    validateConfirmation() {
        const confirmInput = document.getElementById('confirmationInput');
        const proceedBtn = document.getElementById('proceedBtn');
        
        if (confirmInput && proceedBtn) {
            const isValid = confirmInput.value.toUpperCase() === 'CONFIRM';
            proceedBtn.disabled = !isValid;
            
            if (isValid) {
                proceedBtn.style.background = 'linear-gradient(135deg, #27ae60, #229954)';
            } else {
                proceedBtn.style.background = '#95a5a6';
            }
        }
    }
    
    addLogEntry(message, type = 'info', timestamp = null) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;
        
        const entry = document.createElement('div');
        const logTimestamp = timestamp || new Date().toLocaleTimeString();
        
        entry.className = `log-entry log-${type}`;
        entry.innerHTML = `
            <span class="status-icon icon-${type}"></span>
            <span class="timestamp">[${logTimestamp}]</span>
            <span class="message">${this.escapeHtml(message)}</span>
        `;
        
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        this.results.push({
            timestamp: logTimestamp,
            type: type,
            message: message
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    updateProgress(percentage, text = null) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        if (progressFill) {
            progressFill.style.width = percentage + '%';
        }
        
        if (progressText && text) {
            progressText.textContent = text;
        }
    }
    
    toggleCategory(category) {
        const toggle = document.getElementById(`${category}Toggle`);
        const actions = document.getElementById(`${category}Actions`);
        
        if (!toggle || !actions) return;
        
        toggle.classList.toggle('active');
        actions.classList.toggle('disabled');
        
        if (actions.classList.contains('disabled')) {
            const checkboxes = actions.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => checkbox.checked = false);
            this.addLogEntry(`${category.toUpperCase()} actions disabled`, 'info');
        } else {
            this.addLogEntry(`${category.toUpperCase()} actions enabled`, 'info');
        }
        
        this.validateForm();
    }
    
    getSelectedActions() {
        const actions = {};
        const categories = ['ad', 'm365', 'mfa', 'org'];
        
        categories.forEach(category => {
            const categoryActions = document.getElementById(`${category}Actions`);
            const isEnabled = categoryActions && !categoryActions.classList.contains('disabled');
            
            actions[`${category}Actions`] = isEnabled;
            
            if (isEnabled) {
                const checkboxes = categoryActions.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    actions[checkbox.id] = checkbox.checked;
                });
            }
        });
        
        return actions;
    }
    
    getAdCredentials() {
        return {
            username: document.getElementById('adUsername')?.value.trim() || '',
            password: document.getElementById('adPassword')?.value.trim() || ''
        };
    }
    
    async testConnections() {
        if (this.isProcessing) return;
        
        const adCreds = this.getAdCredentials();
        if (!adCreds.username || !adCreds.password) {
            this.addLogEntry('❌ Please enter AD credentials before testing connections', 'error');
            return;
        }
        
        const testBtn = document.getElementById('testBtn');
        if (!testBtn) return;
        
        const originalText = testBtn.textContent;
        testBtn.disabled = true;
        testBtn.textContent = '🔄 Testing...';
        
        this.addLogEntry('Starting connection tests with provided credentials...', 'info');
        this.updateProgress(10, 'Testing connections...');
        
        try {
            const response = await fetch('/test-connections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    adUsername: adCreds.username,
                    adPassword: adCreds.password
                })
            });
            
            const data = await response.json();
            
            if (response.status === 401) {
                this.addLogEntry('❌ Authentication session expired. Please refresh and log in again.', 'error');
                setTimeout(() => window.location.reload(), 2000);
                return;
            }
            
            if (response.ok) {
                this.updateProgress(100, 'Tests completed');
                
                // Update status indicators
                document.getElementById('graphStatus').textContent = 
                    data.graph ? '✅ Connected via user session' : '❌ Session expired';
                document.getElementById('adStatus').textContent = 
                    data.ad ? '✅ Connected successfully' : '❌ Authentication failed';
                document.getElementById('serviceStatus').textContent = 
                    data.service ? '✅ Credentials valid' : '❌ Invalid credentials';
                document.getElementById('ouStatus').textContent = 
                    data.ou ? '✅ OU accessible' : '❌ OU not found';
                
                // Show any additional messages from the server
                if (data.messages) {
                    data.messages.forEach(msg => {
                        this.addLogEntry(msg.message, msg.status);
                    });
                }
                
                const successCount = Object.values(data).filter(Boolean).length;
                const totalTests = 4; // graph, ad, service, ou
                
                this.addLogEntry(
                    `Connection tests completed: ${successCount}/${totalTests} successful`,
                    successCount === totalTests ? 'success' : 'warning'
                );
                
                if (data.ad) {
                    this.addLogEntry(`✅ AD authentication successful for: ${adCreds.username}`, 'success');
                } else {
                    this.addLogEntry(`❌ AD authentication failed for: ${adCreds.username}`, 'error');
                }
                
            } else {
                this.addLogEntry(`Connection test failed: ${data.error}`, 'error');
                this.updateProgress(0, 'Test failed');
            }
        } catch (error) {
            this.addLogEntry(`Connection error: ${error.message}`, 'error');
            this.updateProgress(0, 'Test failed');
        }
        
        setTimeout(() => {
            testBtn.disabled = false;
            testBtn.textContent = originalText;
            this.updateProgress(0, 'Ready');
        }, 2000);
    }
    
    startDeprovisioning() {
        if (this.isProcessing || !this.validateForm()) return;
        
        const userEmail = document.getElementById('userEmail').value.trim();
        const adCreds = this.getAdCredentials();
        
        // Show confirmation modal
        const modal = document.getElementById('confirmationModal');
        const confirmEmail = document.getElementById('confirmUserEmail');
        const confirmAdUser = document.getElementById('confirmAdUser');
        const confirmInput = document.getElementById('confirmationInput');
        
        if (modal && confirmEmail && confirmAdUser && confirmInput) {
            confirmEmail.textContent = userEmail;
            confirmAdUser.textContent = adCreds.username;
            confirmInput.value = '';
            modal.style.display = 'flex';
            confirmInput.focus();
            this.validateConfirmation();
        }
    }
    
    closeConfirmation() {
        const modal = document.getElementById('confirmationModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    async proceedWithDeprovisioning() {
        const userEmail = document.getElementById('userEmail').value.trim();
        const actions = this.getSelectedActions();
        const adCreds = this.getAdCredentials();
        
        this.closeConfirmation();
        
        this.isProcessing = true;
        const deprovisionBtn = document.getElementById('deprovisionBtn');
        const testBtn = document.getElementById('testBtn');
        
        if (deprovisionBtn) {
            deprovisionBtn.disabled = true;
            deprovisionBtn.textContent = '🔄 Processing...';
        }
        
        if (testBtn) {
            testBtn.disabled = true;
        }
        
        this.updateProgress(5, 'Starting...');
        this.addLogEntry(`🚨 DEPROVISIONING STARTED for: ${userEmail}`, 'warning');
        this.addLogEntry(`Using AD credentials: ${adCreds.username}`, 'info');
        
        try {
            const response = await fetch('/deprovision', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userEmail: userEmail,
                    actions: actions,
                    adUsername: adCreds.username,
                    adPassword: adCreds.password
                })
            });
            
            const data = await response.json();
            
            if (response.status === 401) {
                this.addLogEntry('❌ Authentication session expired. Please refresh and log in again.', 'error');
                setTimeout(() => window.location.reload(), 3000);
                return;
            }
            
            if (response.ok && data.results) {
                await this.processResults(data.results, data.password);
            } else {
                this.addLogEntry(`❌ Process failed: ${data.error}`, 'error');
                this.updateProgress(0, 'Failed');
            }
            
        } catch (error) {
            this.addLogEntry(`❌ Network error: ${error.message}`, 'error');
            this.updateProgress(0, 'Error');
        }
        
        setTimeout(() => {
            this.isProcessing = false;
            if (deprovisionBtn) {
                deprovisionBtn.disabled = false;
                deprovisionBtn.textContent = '🚨 Start Deprovisioning';
            }
            if (testBtn) {
                testBtn.disabled = false;
            }
            this.validateForm();
        }, 3000);
    }
    
    async processResults(results, password) {
        let successCount = 0;
        const totalCount = results.length;
        
        for (let i = 0; i < results.length; i++) {
            const result = results[i];
            
            await this.sleep(300);
            
            this.addLogEntry(result.message, result.status);
            
            if (result.status === 'success') {
                successCount++;
            }
            
            const progress = ((i + 1) / totalCount) * 90;
            this.updateProgress(progress, `Processing... ${i + 1}/${totalCount}`);
        }
        
        await this.sleep(500);
        this.updateProgress(100, 'Completed');
        
        const completionMessage = `🎉 Process completed! ${successCount}/${totalCount} actions successful`;
        this.addLogEntry(completionMessage, successCount === totalCount ? 'success' : 'warning');
        
        if (password) {
            await this.sleep(800);
            this.displayPassword(password);
        }
    }
    
    displayPassword(password) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;
        
        const passwordDiv = document.createElement('div');
        passwordDiv.className = 'password-output';
        passwordDiv.innerHTML = `
            <div class="password-label">🔐 Generated Password (SAVE IMMEDIATELY):</div>
            <div class="password-value">${password}</div>
            <div style="margin-top: 15px; font-size: 0.9em; color: #95a5a6;">
                ⚠️ This password excludes the user's first and last name.<br>
                📋 Copy this password now - it will not be shown again!<br>
                🔐 Store securely according to your organization's password policy.
            </div>
            <button onclick="app.copyPassword('${password}')" 
                    style="margin-top: 15px; padding: 10px 20px; background: #27ae60; 
                           color: white; border: none; border-radius: 6px; cursor: pointer;
                           font-weight: bold;">
                📋 Copy to Clipboard
            </button>
        `;
        
        logContainer.appendChild(passwordDiv);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        this.currentPassword = password;
        this.addLogEntry('✅ Password generated and displayed above - copy immediately!', 'success');
    }
    
    async copyPassword(password) {
        try {
            await navigator.clipboard.writeText(password);
            this.addLogEntry('📋 Password copied to clipboard successfully', 'success');
            
            // Provide visual feedback
            const copyBtn = event.target;
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '✅ Copied!';
            copyBtn.style.background = '#27ae60';
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.style.background = '#27ae60';
            }, 2000);
            
        } catch (err) {
            // Fallback for older browsers
            try {
                const textarea = document.createElement('textarea');
                textarea.value = password;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                
                this.addLogEntry('📋 Password copied to clipboard (fallback method)', 'success');
            } catch (fallbackErr) {
                this.addLogEntry('❌ Failed to copy password to clipboard', 'error');
                this.addLogEntry('💡 Please manually select and copy the password above', 'info');
            }
        }
    }
    
    clearLog() {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;
        
        logContainer.innerHTML = '';
        this.results = [];
        this.currentPassword = null;
        
        this.updateProgress(0, 'Ready');
        this.addLogEntry('Log cleared. System ready for new operations.', 'info');
    }
    
    // Security helper to clear sensitive data
    clearSensitiveData() {
        const adPassword = document.getElementById('adPassword');
        if (adPassword) {
            adPassword.value = '';
        }
        
        this.currentPassword = null;
        
        // Clear any password displays
        const passwordOutputs = document.querySelectorAll('.password-output');
        passwordOutputs.forEach(output => {
            output.style.display = 'none';
        });
    }
    
    // Form validation helpers
    showFieldError(fieldId, message) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.style.borderColor = '#e74c3c';
            field.style.boxShadow = '0 0 0 3px rgba(231, 76, 60, 0.1)';
        }
        this.addLogEntry(message, 'error');
    }
    
    showFieldSuccess(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.style.borderColor = '#27ae60';
            field.style.boxShadow = '0 0 0 3px rgba(39, 174, 96, 0.1)';
        }
    }
    
    // Enhanced credential validation
    validateAdCredentials() {
        const username = document.getElementById('adUsername')?.value.trim();
        const password = document.getElementById('adPassword')?.value.trim();
        
        if (!username) {
            this.showFieldError('adUsername', 'AD username is required');
            return false;
        }
        
        if (!password) {
            this.showFieldError('adPassword', 'AD password is required');
            return false;
        }
        
        // Basic format validation
        if (username.length < 3) {
            this.showFieldError('adUsername', 'Username must be at least 3 characters');
            return false;
        }
        
        if (password.length < 8) {
            this.showFieldError('adPassword', 'Password seems too short');
            return false;
        }
        
        this.showFieldSuccess('adUsername');
        this.showFieldSuccess('adPassword');
        return true;
    }
    
    // Enhanced email validation
    validateEmail() {
        const email = document.getElementById('userEmail')?.value.trim();
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        
        if (!email) {
            this.showFieldError('userEmail', 'Target user email is required');
            return false;
        }
        
        if (!emailRegex.test(email)) {
            this.showFieldError('userEmail', 'Please enter a valid email address');
            return false;
        }
        
        this.showFieldSuccess('userEmail');
        return true;
    }
    
    // Security warning for production use
    showSecurityReminder() {
        this.addLogEntry('🔒 Security Reminder: Credentials are used only for this session', 'info');
        this.addLogEntry('🛡️ Ensure you have proper authorization before proceeding', 'warning');
    }
    
    async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}


// Global functions for HTML onclick handlers
let app;


function toggleCategory(category) {
    app?.toggleCategory(category);
}


function testConnections() {
    if (app?.validateAdCredentials()) {
        app?.testConnections();
    }
}


function startDeprovisioning() {
    if (app?.validateEmail() && app?.validateAdCredentials()) {
        app?.startDeprovisioning();
    }
}


function clearLog() {
    app?.clearLog();
}


function closeConfirmation() {
    app?.closeConfirmation();
}


function proceedWithDeprovisioning() {
    app?.proceedWithDeprovisioning();
}


// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    app = new UserDeprovisioningApp();
    
    // Auto-populate test email if none present
    const emailInput = document.getElementById('userEmail');
    if (emailInput && !emailInput.value.trim()) {
        emailInput.value = 'Anthony.DiSilvestro@boldt.com';
        app.validateForm();
    }
    
    // Security reminder
    app.showSecurityReminder();
    
    // Auto-focus on AD username field
    const adUsernameInput = document.getElementById('adUsername');
    if (adUsernameInput) {
        setTimeout(() => adUsernameInput.focus(), 1000);
    }
    
    console.log('🔒 User Deprovisioning Tool v2.1 initialized with user authentication');
    console.log('⌨️ Keyboard shortcuts: Esc (close modal), Ctrl+T (test), Ctrl+Enter (start)');
});


// Enhanced error handling
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    if (app) {
        app.addLogEntry(`❌ Application error: ${event.error.message}`, 'error');
    }
});


window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    if (app) {
        app.addLogEntry(`❌ Network or processing error: ${event.reason}`, 'error');
    }
});


// Security: Clear sensitive data on page unload
window.addEventListener('beforeunload', function(event) {
    if (app) {
        app.clearSensitiveData();
    }
    
    if (app?.isProcessing) {
        event.preventDefault();
        event.returnValue = 'Deprovisioning is in progress. Are you sure you want to leave?';
        return event.returnValue;
    }
});


// Security: Clear password field periodically
setInterval(() => {
    const adPassword = document.getElementById('adPassword');
    if (adPassword && !app?.isProcessing && document.hidden) {
        // Clear password if page is not visible and not processing
        adPassword.value = '';
    }
}, 300000); // 5 minutes


// Export the app class for potential external use
window.UserDeprovisioningApp = UserDeprovisioningApp;




