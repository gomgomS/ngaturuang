// Register JavaScript for Money Management AI

// Global variables
let isProcessing = false;

// Initialize registration
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 Registration initialized');
    setupRegisterEventListeners();
});

// Setup registration event listeners
function setupRegisterEventListeners() {
    // Register button
    const registerBtn = document.getElementById('btn-register');
    if (registerBtn) {
        registerBtn.addEventListener('click', handleRegister);
    }
    
    // Password confirmation validation on input
    const passwordInput = document.getElementById('register-password');
    const confirmPasswordInput = document.getElementById('register-confirm-password');
    
    if (confirmPasswordInput && passwordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            validatePasswordMatch();
        });
        
        passwordInput.addEventListener('input', function() {
            validatePasswordMatch();
        });
    }
}

// Validate password match
function validatePasswordMatch() {
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    const confirmInput = document.getElementById('register-confirm-password');
    
    if (confirmPassword && password !== confirmPassword) {
        confirmInput.classList.add('is-invalid');
        confirmInput.classList.remove('is-valid');
    } else if (confirmPassword && password === confirmPassword) {
        confirmInput.classList.remove('is-invalid');
        confirmInput.classList.add('is-valid');
    } else {
        confirmInput.classList.remove('is-invalid', 'is-valid');
    }
}

// Handle user registration
async function handleRegister() {
    if (isProcessing) return;
    
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    
    // Validation
    if (!username || !password || !confirmPassword) {
        showRegisterMessage('Please fill in all fields', 'warning');
        return;
    }
    
    if (username.length < 3) {
        showRegisterMessage('Username must be at least 3 characters long', 'warning');
        return;
    }
    
    if (username.length > 20) {
        showRegisterMessage('Username must be less than 20 characters', 'warning');
        return;
    }
    
    // Username format validation (alphanumeric and underscore only)
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        showRegisterMessage('Username can only contain letters, numbers, and underscores', 'warning');
        return;
    }
    
    if (password.length < 6) {
        showRegisterMessage('Password must be at least 6 characters long', 'warning');
        return;
    }
    
    if (password.length > 50) {
        showRegisterMessage('Password must be less than 50 characters', 'warning');
        return;
    }
    
    // Password strength validation
    if (!/(?=.*[a-z])/.test(password)) {
        showRegisterMessage('Password must contain at least one lowercase letter', 'warning');
        return;
    }
    
    if (!/(?=.*[A-Z])/.test(password)) {
        showRegisterMessage('Password must contain at least one uppercase letter', 'warning');
        return;
    }
    
    if (!/(?=.*\d)/.test(password)) {
        showRegisterMessage('Password must contain at least one number', 'warning');
        return;
    }
    
    if (!/(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?])/.test(password)) {
        showRegisterMessage('Password must contain at least one special character', 'warning');
        return;
    }
    
    // Password confirmation validation
    if (password !== confirmPassword) {
        showRegisterMessage('Passwords do not match', 'warning');
        return;
    }
    
    // reCAPTCHA validation
    const recaptchaResponse = grecaptcha.getResponse();
    if (!recaptchaResponse) {
        showRegisterMessage('Please complete the reCAPTCHA verification', 'warning');
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
            showRegisterMessage('Registration successful! Redirecting to dashboard...', 'success');
            // Reset reCAPTCHA
            grecaptcha.reset();
            // Clear form
            document.getElementById('registerForm').reset();
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            const error = await response.json().catch(() => ({ error: 'Registration failed' }));
            showRegisterMessage(error.error || 'Registration failed. Please try again.', 'danger');
            // Reset reCAPTCHA on error
            grecaptcha.reset();
        }
    } catch (error) {
        console.error('Registration error:', error);
        showRegisterMessage('Network error. Please check your connection and try again.', 'danger');
        // Reset reCAPTCHA on error
        grecaptcha.reset();
    } finally {
        setProcessingState(false);
    }
}

// Show registration message
function showRegisterMessage(message, type = 'info') {
    const msgElement = document.getElementById('register-msg');
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
    const usernameInput = document.getElementById('register-username');
    const passwordInput = document.getElementById('register-password');
    const confirmPasswordInput = document.getElementById('register-confirm-password');
    
    if (processing) {
        // Disable inputs and buttons
        if (registerBtn) {
            registerBtn.disabled = true;
            registerBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
        if (usernameInput) usernameInput.disabled = true;
        if (passwordInput) passwordInput.disabled = true;
        if (confirmPasswordInput) confirmPasswordInput.disabled = true;
    } else {
        // Enable inputs and buttons
        if (registerBtn) {
            registerBtn.disabled = false;
            registerBtn.innerHTML = '<i class="fas fa-user-plus me-2"></i>Register';
        }
        if (usernameInput) usernameInput.disabled = false;
        if (passwordInput) passwordInput.disabled = false;
        if (confirmPasswordInput) confirmPasswordInput.disabled = false;
    }
}

// Export functions for global access
window.RegisterManager = {
    handleRegister,
    showRegisterMessage,
    validatePasswordMatch
};
