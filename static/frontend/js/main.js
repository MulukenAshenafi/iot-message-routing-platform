// Store JWT token in localStorage when available
document.addEventListener('DOMContentLoaded', function() {
    // Try to get token from meta tag if available
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (tokenMeta) {
        // Token handling
    }
    
    // Auto-refresh token if needed
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
        // Token refresh logic can be added here
    }
    
    // Add loading states to buttons
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span>Loading...</span>';
                
                // Re-enable after 5 seconds as fallback
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 5000);
            }
        });
    });
});

// Helper function to get CSRF token
function getCSRFToken() {
    // Try window.csrfToken first (set in base template)
    if (typeof window.csrfToken !== 'undefined' && window.csrfToken) {
        return window.csrfToken;
    }
    // Try meta tag
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (tokenMeta) {
        return tokenMeta.getAttribute('content');
    }
    // Fallback to cookie
    return getCookie('csrftoken') || '';
}

// Helper function to get auth headers
function getAuthHeaders(method = 'GET') {
    // Try multiple sources for token
    let token = null;
    if (typeof window !== 'undefined' && window.accessToken) {
        token = window.accessToken;
    }
    if (!token) {
        token = localStorage.getItem('access_token');
    }
    
    const headers = {
        'Content-Type': 'application/json',
    };
    
    // Add JWT token if available
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Add CSRF token for state-changing requests (POST, PUT, PATCH, DELETE)
    // Note: DRF exempts CSRF for JWT auth, but we include it for session-based requests
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
        const csrfToken = getCSRFToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }
    }
    
    return headers;
}

// Helper function to get cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper function to handle API errors
function handleApiError(error) {
    console.error('API Error:', error);
    if (error.status === 401) {
        // Redirect to login if unauthorized
        window.location.href = '/login/';
    }
}

// Add smooth scrolling
document.documentElement.style.scrollBehavior = 'smooth';

