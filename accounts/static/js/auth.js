// Enhanced signup form with real-time validation and better UX

// State management
let otpSent = false;
let otpTimer = null;
let remainingTime = 600; // 10 minutes in seconds

/**
 * Initialize signup form enhancements
 */
document.addEventListener('DOMContentLoaded', function () {
    const emailField = document.getElementById('email');
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('rpassword');
    const otpContainer = document.getElementById('otp-container');

    if (emailField) {
        emailField.addEventListener('blur', handleEmailValidation);
        emailField.addEventListener('input', clearFieldError);
    }

    if (usernameField) {
        usernameField.addEventListener('blur', checkUsernameAvailability);
        usernameField.addEventListener('input', clearFieldError);
    }

    if (passwordField) {
        passwordField.addEventListener('input', updatePasswordStrength);
    }

    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', checkPasswordMatch);
    }
});

/**
 * Handle email validation and auto-send OTP
 */
async function handleEmailValidation() {
    const emailField = document.getElementById('email');
    const email = emailField.value.trim();

    if (!email || !isValidEmail(email)) {
        showFieldError(emailField, 'Please enter a valid email address');
        return;
    }

    // Check if email already exists
    const isAvailable = await checkEmailAvailability(email);
    if (!isAvailable) {
        return; // Error already shown by checkEmailAvailability
    }

    // Auto-send OTP
    await sendOTP(email);
}

/**
 * Validate email format
 */
function isValidEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * Check if username is available
 */
async function checkUsernameAvailability() {
    const usernameField = document.getElementById('username');
    const username = usernameField.value.trim().toLowerCase();

    if (!username) {
        showFieldError(usernameField, 'Username is required');
        return;
    }

    if (username.length < 3) {
        showFieldError(usernameField, 'Username must be at least 3 characters');
        return;
    }

    try {
        const response = await fetch('/check-username/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ username })
        });

        const data = await response.json();

        if (data.available) {
            showFieldSuccess(usernameField);
        } else {
            showFieldError(usernameField, 'Username already taken');
        }
    } catch (error) {
        console.error('Error checking username:', error);
    }
}

/**
 * Check if email is available
 */
async function checkEmailAvailability(email) {
    const emailField = document.getElementById('email');

    try {
        const response = await fetch('/check-email/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (data.available) {
            showFieldSuccess(emailField);
            return true;
        } else {
            showFieldError(emailField, 'Email already registered');
            return false;
        }
    } catch (error) {
        console.error('Error checking email:', error);
        return false;
    }
}

/**
 * Send OTP to email
 */
async function sendOTP(email = null) {
    if (!email) {
        email = document.getElementById('email').value.trim();
    }

    if (!email) {
        showNotification('Please enter your email address', 'error');
        return;
    }

    // Show loading state
    const sendButton = document.getElementById('send-otp-btn');
    if (sendButton) {
        sendButton.disabled = true;
        sendButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Sending...';
    }

    try {
        const response = await fetch('/send-otp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (data.status === 'Success') {
            otpSent = true;
            showOTPField();
            startOTPTimer();
            showNotification('OTP sent successfully! Check your email', 'success');
        } else {
            showNotification(data.message || 'Failed to send OTP', 'error');
        }
    } catch (error) {
        console.error('Error sending OTP:', error);
        showNotification('Failed to send OTP. Please try again', 'error');
    } finally {
        if (sendButton) {
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fa fa-paper-plane"></i>';
        }
    }
}

/**
 * Show OTP field and hide email edit
 */
function showOTPField() {
    const otpContainer = document.getElementById('otp-container');
    const emailField = document.getElementById('email');

    if (otpContainer) {
        otpContainer.style.display = 'block';
        otpContainer.classList.add('fade-in');
    }

    if (emailField) {
        emailField.readOnly = true;
        emailField.style.backgroundColor = '#f0f0f0';
    }
}

/**
 * Start countdown timer for OTP
 */
function startOTPTimer() {
    remainingTime = 600; // Reset to 10 minutes
    updateTimerDisplay();

    if (otpTimer) {
        clearInterval(otpTimer);
    }

    otpTimer = setInterval(() => {
        remainingTime--;
        updateTimerDisplay();

        if (remainingTime <= 0) {
            clearInterval(otpTimer);
            showNotification('OTP expired. Please request a new one', 'warning');
        }
    }, 1000);
}

/**
 * Update timer display
 */
function updateTimerDisplay() {
    const timerElement = document.getElementById('otp-timer');
    if (!timerElement) return;

    const minutes = Math.floor(remainingTime / 60);
    const seconds = remainingTime % 60;
    const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    timerElement.textContent = `Expires in ${timeString}`;

    if (remainingTime < 60) {
        timerElement.classList.add('text-danger');
    }
}

/**
 * Password strength indicator
 */
function updatePasswordStrength() {
    const passwordField = document.getElementById('password');
    const strengthBar = document.getElementById('password-strength');
    const strengthText = document.getElementById('password-strength-text');

    if (!strengthBar || !strengthText) return;

    const password = passwordField.value;
    const strength = calculatePasswordStrength(password);

    strengthBar.style.width = `${strength.percentage}%`;
    strengthBar.className = `password-strength-bar ${strength.class}`;
    strengthText.textContent = strength.text;
    strengthText.className = `password-strength-text ${strength.class}`;
}

/**
 * Calculate password strength
 */
function calculatePasswordStrength(password) {
    let strength = 0;

    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 15;
    if (/[a-z]/.test(password)) strength += 15;
    if (/[A-Z]/.test(password)) strength += 15;
    if (/[0-9]/.test(password)) strength += 15;
    if (/[^a-zA-Z0-9]/.test(password)) strength += 15;

    if (strength < 40) {
        return { percentage: strength, class: 'weak', text: 'Weak' };
    } else if (strength < 70) {
        return { percentage: strength, class: 'medium', text: 'Medium' };
    } else {
        return { percentage: strength, class: 'strong', text: 'Strong' };
    }
}

/**
 * Check password match
 */
function checkPasswordMatch() {
    const passwordField = document.getElementById('password');
    const confirmPasswordField = document.getElementById('rpassword');

    if (confirmPasswordField.value === '') {
        clearFieldError(confirmPasswordField);
        return;
    }

    if (passwordField.value === confirmPasswordField.value) {
        showFieldSuccess(confirmPasswordField);
    } else {
        showFieldError(confirmPasswordField, 'Passwords do not match');
    }
}

/**
 * Show field error
 */
function showFieldError(field, message) {
    clearFieldError(field);

    field.classList.add('is-invalid');
    field.classList.remove('is-valid');

    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

/**
 * Show field success
 */
function showFieldSuccess(field) {
    clearFieldError(field);

    field.classList.add('is-valid');
    field.classList.remove('is-invalid');
}

/**
 * Clear field error
 */
function clearFieldError(field) {
    if (field.target) {
        field = field.target;
    }

    field.classList.remove('is-invalid', 'is-valid');
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

/**
 * Get CSRF token
 */
function getCSRFToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}

/**
 * Legacy function for backward compatibility
 */
function get_otp(csrf) {
    sendOTP();
}
