"""
Simple rate limiting middleware for myHelperBuddy.
Implements IP-based rate limiting for sensitive endpoints.
"""

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.conf import settings
import time


class SimpleRateLimitMiddleware:
    """
    Simple rate limiting middleware using Django's cache framework.
    """
    
    # Define rate limits: (requests, time_window_in_seconds)
    RATE_LIMITS = {
        '/login': (5, 300),  # 5 requests per 5 minutes
        '/send-otp/': (3, 300),  # 3 requests per 5 minutes
        '/forgotPassword/': (3, 600),  # 3 requests per 10 minutes
        '/signup/': (5, 600),  # 5 requests per 10 minutes
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if rate limiting should be applied
        path = request.path
        
        if path in self.RATE_LIMITS:
            # Get client IP
            ip_address = self.get_client_ip(request)
            
            # Check rate limit
            if not self.check_rate_limit(ip_address, path):
                return HttpResponseForbidden(
                    "Rate limit exceeded. Please try again later."
                )
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def check_rate_limit(self, ip_address, path):
        """
        Check if the request is within rate limits.
        Returns True if allowed, False if rate limit exceeded.
        """
        max_requests, time_window = self.RATE_LIMITS[path]
        
        cache_key = f'rate_limit:{path}:{ip_address}'
        
        # Get current request data from cache
        request_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time() + time_window})
        
        current_time = time.time()
        
        # Reset if time window has passed
        if current_time > request_data['reset_time']:
            request_data = {'count': 1, 'reset_time': current_time + time_window}
            cache.set(cache_key, request_data, time_window)
            return True
        
        # Check if limit exceeded
        if request_data['count'] >= max_requests:
            return False
        
        # Increment counter
        request_data['count'] += 1
        remaining_time = int(request_data['reset_time'] - current_time)
        cache.set(cache_key, request_data, remaining_time)
        
        return True


# Alternative: Function-based rate limit decorator for specific views
def rate_limit(max_requests=5, time_window=300):
    """
    Decorator for rate limiting specific views.
    
    Usage:
        @rate_limit(max_requests=5, time_window=300)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            ip_address = get_client_ip(request)
            cache_key = f'rate_limit:{view_func.__name__}:{ip_address}'
            
            request_data = cache.get(cache_key, {'count': 0, 'reset_time': time.time() + time_window})
            current_time = time.time()
            
            if current_time > request_data['reset_time']:
                request_data = {'count': 1, 'reset_time': current_time + time_window}
                cache.set(cache_key, request_data, time_window)
            elif request_data['count'] >= max_requests:
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
            else:
                request_data['count'] += 1
                remaining_time = int(request_data['reset_time'] - current_time)
                cache.set(cache_key, request_data, remaining_time)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def get_client_ip(request):
    """Helper function to extract client IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
