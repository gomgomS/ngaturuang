// Authentication JavaScript for Money Management AI

// Global variables
let isProcessing = false;

// Initialize authentication
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 Authentication initialized');
    setupAuthEventListeners();
});

// Setup authentication event listeners
function setupAuthEventListeners() {
    // Register button
    const registerBtn = document.getElementById('btn-register');
    if (registerBtn) {
        registerBtn.addEventListener('click', handleRegister);
    }
    
    // Login button
    const loginBtn = document.getElementById('btn-login');
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }
    
    // Form submission on Enter key
    const usernameInput = document.getElementById('auth-username');
    const passwordInput = document.getElementById('auth-password');
    
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

// Handle user registration
async function handleRegister() {
    if (isProcessing) return;
    
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    const confirmPassword = document.getElementById('auth-confirm-password').value;
    
    // Validation
    if (!username || !password || !confirmPassword) {
        showAuthMessage('Please fill in all fields', 'warning');
        return;
    }
    
    if (username.length < 3) {
        showAuthMessage('Username must be at least 3 characters long', 'warning');
        return;
    }
    
    if (username.length > 20) {
        showAuthMessage('Username must be less than 20 characters', 'warning');
        return;
    }
    
    // Username format validation (alphanumeric and underscore only)
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        showAuthMessage('Username can only contain letters, numbers, and underscores', 'warning');
        return;
    }
    
    if (password.length < 6) {
        showAuthMessage('Password must be at least 6 characters long', 'warning');
        return;
    }
    
    if (password.length > 50) {
        showAuthMessage('Password must be less than 50 characters', 'warning');
        return;
    }
    
    // Password strength validation
    if (!/(?=.*[a-z])/.test(password)) {
        showAuthMessage('Password must contain at least one lowercase letter', 'warning');
        return;
    }
    
    if (!/(?=.*[A-Z])/.test(password)) {
        showAuthMessage('Password must contain at least one uppercase letter', 'warning');
        return;
    }
    
    if (!/(?=.*\d)/.test(password)) {
        showAuthMessage('Password must contain at least one number', 'warning');
        return;
    }
    
    if (!/(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?])/.test(password)) {
        showAuthMessage('Password must contain at least one special character', 'warning');
        return;
    }
    
    // Password confirmation validation
    if (password !== confirmPassword) {
        showAuthMessage('Passwords do not match', 'warning');
        return;
    }
    
    // reCAPTCHA validation
    const recaptchaResponse = grecaptcha.getResponse();
    if (!recaptchaResponse) {
        showAuthMessage('Please complete the reCAPTCHA verification', 'warning');
        return;
    }
    
    setProcessingState(true);
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                username, 
                password,
                recaptcha_response: recaptchaResponse
            })
        });
        
        if (response.ok) {
            showAuthMessage('Registration successful! Redirecting to dashboard...', 'success');
            // Reset reCAPTCHA
            grecaptcha.reset();
            // Clear form
            document.getElementById('authForm').reset();
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            const error = await response.json().catch(() => ({ error: 'Registration failed' }));
            showAuthMessage(error.error || 'Registration failed. Please try again.', 'danger');
            // Reset reCAPTCHA on error
            grecaptcha.reset();
        }
    } catch (error) {
        console.error('Registration error:', error);
        showAuthMessage('Network error. Please check your connection and try again.', 'danger');
        // Reset reCAPTCHA on error
        grecaptcha.reset();
    } finally {
        setProcessingState(false);
    }
}

// Handle user login
async function handleLogin() {
    if (isProcessing) return;
    
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value;
    
    // Validation
    if (!username || !password) {
        showAuthMessage('Please fill in both username and password', 'warning');
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
            showAuthMessage('Login successful! Redirecting to dashboard...', 'success');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            const error = await response.json().catch(() => ({ error: 'Login failed' }));
            showAuthMessage(error.error || 'Invalid username or password. Please try again.', 'danger');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAuthMessage('Network error. Please check your connection and try again.', 'danger');
    } finally {
        setProcessingState(false);
    }
}

// Show authentication message
function showAuthMessage(message, type = 'info') {
    const msgElement = document.getElementById('auth-msg');
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
    
    const registerBtn = document.getElementById('btn-register');
    const loginBtn = document.getElementById('btn-login');
    const usernameInput = document.getElementById('auth-username');
    const passwordInput = document.getElementById('auth-password');
    
    if (processing) {
        // Disable inputs and buttons
        if (registerBtn) {
            registerBtn.disabled = true;
            registerBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
        if (loginBtn) {
            loginBtn.disabled = true;
            loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
        if (usernameInput) usernameInput.disabled = true;
        if (passwordInput) passwordInput.disabled = true;
    } else {
        // Enable inputs and buttons
        if (registerBtn) {
            registerBtn.disabled = false;
            registerBtn.innerHTML = '<i class="fas fa-user-plus me-2"></i>Register';
        }
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
    const usernameInput = document.getElementById('auth-username');
    const passwordInput = document.getElementById('auth-password');
    
    if (usernameInput && passwordInput) {
        usernameInput.value = 'demo_user';
        passwordInput.value = 'demo123';
        
        showAuthMessage('Demo mode: Credentials auto-filled. Click Login to continue.', 'info');
    }
}

// Auto-enable demo mode after 3 seconds if no interaction
setTimeout(() => {
    const usernameInput = document.getElementById('auth-username');
    if (usernameInput && !usernameInput.value) {
        enableDemoMode();
    }
}, 3000);

// Export functions for global access
window.AuthManager = {
    handleRegister,
    handleLogin,
    showAuthMessage,
    enableDemoMode
};


