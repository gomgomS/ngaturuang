// Login JavaScript for Money Management AI

// Global variables
let isProcessing = false;

// Initialize login
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 Login initialized');
    setupLoginEventListeners();
});

// Setup login event listeners
function setupLoginEventListeners() {
    // Login button
    const loginBtn = document.getElementById('btn-login');
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }
    
    // Form submission on Enter key
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    
    if (usernameInput && passwordInput) {
        [usernameInput, passwordInput].forEach(input => {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleLogin();
                }
            });
        });
    }
}

// Handle user login
async function handleLogin() {
    if (isProcessing) return;
    
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    
    // Validation
    if (!username || !password) {
        showLoginMessage('Please fill in both username and password', 'warning');
        return;
    }
    
    setProcessingState(true);
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            showLoginMessage('Login successful! Redirecting to dashboard...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            const error = await response.json().catch(() => ({ error: 'Login failed' }));
            showLoginMessage(error.error || 'Invalid username or password. Please try again.', 'danger');
        }
    } catch (error) {
        console.error('Login error:', error);
        showLoginMessage('Network error. Please check your connection and try again.', 'danger');
    } finally {
        setProcessingState(false);
    }
}

// Show login message
function showLoginMessage(message, type = 'info') {
    const msgElement = document.getElementById('login-msg');
    if (!msgElement) return;
    
    // Remove existing classes
    msgElement.className = 'alert alert-dismissible fade show';
    
    // Add type-specific classes
    switch (type) {
        case 'success':
            msgElement.classList.add('alert-success');
            break;
        case 'danger':
            msgElement.classList.add('alert-danger');
            break;
        case 'warning':
            msgElement.classList.add('alert-warning');
            break;
        default:
            msgElement.classList.add('alert-info');
    }
    
    // Set message content
    msgElement.innerHTML = `
        <i class="fas fa-${getIconForType(type)} me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Show message
    msgElement.classList.remove('d-none');
    
    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            if (msgElement.parentNode) {
                msgElement.classList.add('d-none');
            }
        }, 5000);
    }
}

// Get icon for message type
function getIconForType(type) {
    switch (type) {
        case 'success':
            return 'check-circle';
        case 'danger':
            return 'exclamation-triangle';
        case 'warning':
            return 'exclamation-circle';
        default:
            return 'info-circle';
    }
}

// Set processing state
function setProcessingState(processing) {
    isProcessing = processing;
    
    const loginBtn = document.getElementById('btn-login');
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    
    if (processing) {
        // Disable inputs and buttons
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
        if (usernameInput) usernameInput.disabled = true;
        if (passwordInput) passwordInput.disabled = true;
    } else {
        // Enable inputs and buttons
        if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Login';
        }
        if (usernameInput) usernameInput.disabled = false;
        if (passwordInput) passwordInput.disabled = false;
    }
}

// Demo mode functions (for development/testing)
function enableDemoMode() {
    console.log('🎭 Demo mode enabled');
    
    // Auto-fill demo credentials
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    
    if (usernameInput && passwordInput) {
        usernameInput.value = 'demo_user';
        passwordInput.value = 'demo123';
        
        showLoginMessage('Demo mode: Credentials auto-filled. Click Login to continue.', 'info');
    }
}

// Auto-enable demo mode after 3 seconds if no interaction
setTimeout(() => {
    const usernameInput = document.getElementById('login-username');
    if (usernameInput && !usernameInput.value) {
        enableDemoMode();
    }
}, 3000);

// Export functions for global access
window.LoginManager = {
    handleLogin,
    showLoginMessage,
    enableDemoMode
};
