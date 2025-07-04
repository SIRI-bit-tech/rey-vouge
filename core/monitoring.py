import time
import functools
import logging
from django.conf import settings
from django.core.cache import cache
from actstream import action
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger('rey_vogue.performance')
security_logger = logging.getLogger('rey_vogue.security')

def log_performance(func):
    """Decorator to log function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logger.info(
            'Performance metric',
            extra={
                'function': func.__name__,
                'execution_time': execution_time,
                'args': str(args),
                'kwargs': str(kwargs)
            }
        )
        
        # Log if execution time is too long
        if execution_time > 1.0:  # 1 second threshold
            logger.warning(
                f"Slow execution detected in {func.__name__}",
                extra={
                    'execution_time': execution_time,
                    'function': func.__name__
                }
            )
        
        return result
    return wrapper

def log_user_activity(user, verb, action_object=None, target=None, **kwargs):
    """Log user activity using django-activity-stream"""
    try:
        action.send(
            user,
            verb=verb,
            action_object=action_object,
            target=target,
            **kwargs
        )
    except Exception as e:
        logger.error(
            'Failed to log user activity',
            extra={
                'user': user.id if user else None,
                'verb': verb,
                'error': str(e)
            }
        )

def log_security_event(event_type, user=None, ip_address=None, details=None):
    """Log security-related events"""
    security_logger.info(
        'Security event',
        extra={
            'event_type': event_type,
            'user_id': user.id if user else None,
            'username': user.username if user else None,
            'ip_address': ip_address,
            'details': details
        }
    )
    
    # Log critical security events with higher severity
    if event_type in ['unauthorized_access', 'suspicious_activity', 'brute_force_attempt']:
        security_logger.warning(
            f"Critical security event: {event_type}",
            extra={
                'user_id': user.id if user else None,
                'ip_address': ip_address,
                'details': details
            }
        )

def rate_limit(key_prefix, limit=100, period=3600):
    """Rate limiting decorator"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"rate_limit:{key_prefix}:{time.time() // period}"
            current = cache.get(key, 0)
            
            if current >= limit:
                log_security_event(
                    'rate_limit_exceeded',
                    details={
                        'key_prefix': key_prefix,
                        'limit': limit,
                        'period': period
                    }
                )
                raise Exception('Rate limit exceeded')
            
            cache.set(key, current + 1, period)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def setup_monitoring(request):
    """Setup monitoring context for each request"""
    # Basic request monitoring setup
    if hasattr(request, 'session'):
        logger.info('Request started', extra={
            'session_id': request.session.session_key,
            'path': request.path,
            'method': request.method,
            'user_id': request.user.id if request.user.is_authenticated else None
        }) 