from django.conf import settings

def error_tracking_settings(request):
    return {
        'BUGSNAG_API_KEY': settings.BUGSNAG_API_KEY if hasattr(settings, 'BUGSNAG_API_KEY') else None,
        'ENVIRONMENT': settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'development',
    }

def breadcrumbs(request):
    """
    Adds breadcrumb data to the context.
    """
    path_parts = [p for p in request.path.split('/') if p]
    breadcrumbs = []
    current_path = ''
    
    for part in path_parts:
        current_path += f'/{part}'
        breadcrumbs.append({
            'name': part.replace('-', ' ').title(),
            'url': current_path
        })
    
    return {
        'breadcrumbs': breadcrumbs
    } 