from django.conf import settings

def error_tracking_settings(request):
    return {
        'BUGSNAG_API_KEY': settings.BUGSNAG_API_KEY if hasattr(settings, 'BUGSNAG_API_KEY') else None,
        'ENVIRONMENT': settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'development',
    } 