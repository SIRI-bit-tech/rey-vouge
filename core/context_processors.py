from django.conf import settings

def error_tracking_settings(request):
    return {
        'BUGSNAG_API_KEY': settings.BUGSNAG_API_KEY if hasattr(settings, 'BUGSNAG_API_KEY') else None,
        'ENVIRONMENT': settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'development',
    }

def breadcrumbs(request):
    """
    Adds breadcrumb data to the context.
    Only shows breadcrumbs on specific pages.
    """
    # List of URL patterns where breadcrumbs should be shown
    breadcrumb_paths = [
        '/products/',
        '/checkout/',
        '/orders/',
        '/cart/',
    ]
    
    # Check if current path should show breadcrumbs
    show_breadcrumbs = any(request.path.startswith(path) for path in breadcrumb_paths)
    
    if not show_breadcrumbs:
        return {'show_breadcrumbs': False, 'breadcrumbs': []}
    
    path_parts = [p for p in request.path.split('/') if p]
    breadcrumbs = []
    current_path = ''
    
    # Add home as first breadcrumb
    breadcrumbs.append({
        'name': 'Home',
        'url': '/'
    })
    
    # Add subsequent breadcrumbs
    for part in path_parts:
        current_path += f'/{part}'
        name = part.replace('-', ' ').title()
        # Customize names for specific sections
        if part == 'products':
            name = 'Shop'
        elif part == 'checkout':
            name = 'Checkout'
        
        breadcrumbs.append({
            'name': name,
            'url': current_path
        })
    
    return {
        'show_breadcrumbs': True,
        'breadcrumbs': breadcrumbs
    } 