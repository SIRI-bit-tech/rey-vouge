from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from rest_framework import generics, permissions
from rest_framework.response import Response
import os
from django.conf import settings
from rest_framework.views import APIView
from products.models import Category, Product
from .models import (
    Wishlist, NewsletterSubscriber, ContactMessage,
    Promotion, StoreLocation
)
from .serializers import (
    WishlistSerializer, NewsletterSubscriberSerializer,
    ContactMessageSerializer, PromotionSerializer,
    StoreLocationSerializer
)
from django.contrib.sites.shortcuts import get_current_site
import logging
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
import json

logger = logging.getLogger('django')

def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_featured=True)[:8]
    new_arrivals = Product.objects.filter(is_new_arrival=True)[:8]
    promotions = Promotion.objects.filter(is_active=True)[:3]
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'promotions': promotions,
    }
    return render(request, 'core/home.html', context)

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Save to database
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        
        # Send email notification to admin
        admin_email = os.getenv('ADMIN_EMAIL')
        email_subject = f'New Contact Message: {subject}'
        email_message = f"""
        New contact form submission:
        
        From: {name} ({email})
        Subject: {subject}
        Message:
        {message}
        """
        
        try:
            send_mail(
                subject=email_subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False
            )
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Your message has been sent successfully!'
        })
    
    return render(request, 'core/contact.html')

@login_required
def admin_newsletter(request):
    if not request.user.is_staff:
        return JsonResponse({
            'success': False, 
            'message': 'Permission denied'
        }, status=403)
    
    subscribers = NewsletterSubscriber.objects.all().order_by('-created_at')
    context = {
        'subscribers': subscribers,
        'total_subscribers': subscribers.filter(is_active=True).count(),
        'inactive_subscribers': subscribers.filter(is_active=False).count()
    }
    return render(request, 'core/admin/newsletter.html', context)

@login_required
def delete_subscriber(request, subscriber_id):
    if not request.user.is_staff:
        return JsonResponse({
            'success': False, 
            'message': 'Permission denied'
        }, status=403)
    
    try:
        subscriber = NewsletterSubscriber.objects.get(id=subscriber_id)
        subscriber.delete()
        return JsonResponse({
            'success': True,
            'message': f'Subscriber {subscriber.email} has been deleted'
        })
    except NewsletterSubscriber.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Subscriber not found'
        }, status=404)

def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a valid email address.'
            }, status=400)
            
        try:
            # Check if email is already subscribed
            subscriber = NewsletterSubscriber.objects.filter(email=email).first()
            
            if subscriber:
                if not subscriber.is_active:
                    # Reactivate subscription
                    subscriber.is_active = True
                    subscriber.save()
                    
                    # Send reactivation email
                    current_site = get_current_site(request)
                    site_url = f"https://{current_site.domain}" if request.is_secure() else f"http://{current_site.domain}"
                    
                    context = {
                        'email': email,
                        'site_url': site_url,
                        'unsubscribe_url': f"{site_url}/newsletter/unsubscribe/"
                    }
                    
                    html_message = render_to_string('core/emails/newsletter_reactivation.html', context)
                    send_mail(
                        subject="Welcome Back to REY PREMIUM VOGUE Newsletter!",
                        message='',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        html_message=html_message,
                        fail_silently=False
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Your subscription has been reactivated!'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'This email is already subscribed to our newsletter.'
                    })
            else:
                # Create new subscription
                NewsletterSubscriber.objects.create(email=email)
                
                # Send welcome email
                current_site = get_current_site(request)
                site_url = f"https://{current_site.domain}" if request.is_secure() else f"http://{current_site.domain}"
                
                context = {
                    'email': email,
                    'site_url': site_url,
                    'unsubscribe_url': f"{site_url}/newsletter/unsubscribe/"
                }
                
                html_message = render_to_string('core/emails/newsletter_welcome.html', context)
                send_mail(
                    subject="Welcome to REY PREMIUM VOGUE Newsletter!",
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Thank you for subscribing to our newsletter!'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'An error occurred. Please try again.'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)

@login_required
def send_newsletter(request):
    if not request.user.is_staff:
        return JsonResponse({
            'success': False, 
            'message': 'Permission denied'
        }, status=403)
        
    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        
        if not subject or not content:
            return JsonResponse({
                'success': False,
                'message': 'Subject and content are required'
            }, status=400)
            
        try:
            # Get all active subscribers
            subscribers = NewsletterSubscriber.objects.filter(is_active=True)
            total_subscribers = subscribers.count()
            
            if total_subscribers == 0:
                return JsonResponse({
                    'success': False,
                    'message': 'No active subscribers found.'
                })
            
            # Prepare email template
            current_site = get_current_site(request)
            site_url = f"https://{current_site.domain}" if request.is_secure() else f"http://{current_site.domain}"
            
            context = {
                'subject': subject,
                'content': content,
                'site_url': site_url,
                'unsubscribe_url': f"{site_url}/newsletter/unsubscribe/"
            }
            
            html_message = render_to_string('core/emails/newsletter_update.html', context)
            
            # Send emails in batches to avoid timeout
            BATCH_SIZE = 50
            successful_sends = 0
            failed_sends = 0
            
            for i in range(0, total_subscribers, BATCH_SIZE):
                batch = subscribers[i:i + BATCH_SIZE]
                recipient_list = [subscriber.email for subscriber in batch]
                
                try:
                    send_mail(
                        subject=f"{subject} - REY PREMIUM VOGUE",
                        message='',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=recipient_list,
                        html_message=html_message
                    )
                    successful_sends += len(recipient_list)
                except Exception as e:
                    failed_sends += len(recipient_list)
                    print(f"Failed to send newsletter batch: {str(e)}")
            
            message = f"Newsletter sent to {successful_sends} subscribers successfully."
            if failed_sends > 0:
                message += f" Failed to send to {failed_sends} subscribers."
            
            return JsonResponse({
                'success': True,
                'message': message,
                'details': {
                    'total_subscribers': total_subscribers,
                    'successful_sends': successful_sends,
                    'failed_sends': failed_sends
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred while sending the newsletter: {str(e)}'
            }, status=500)
    
    return render(request, 'core/admin/send_newsletter.html')

@login_required
def wishlist(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    context = {
        'wishlist': wishlist,
    }
    return render(request, 'core/wishlist.html', context)

@login_required
def add_to_wishlist(request, product_id):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    product = get_object_or_404(Product, id=product_id)
    
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        message = 'Product removed from wishlist'
    else:
        wishlist.products.add(product)
        message = 'Product added to wishlist'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'count': wishlist.products.count()
    })

@login_required
def remove_from_wishlist(request, product_id):
    wishlist = get_object_or_404(Wishlist, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    
    wishlist.products.remove(product)
    
    return JsonResponse({
        'success': True,
        'message': 'Product removed from wishlist',
        'count': wishlist.products.count()
    })

def store_locations(request):
    locations = StoreLocation.objects.filter(is_active=True)
    context = {
        'locations': locations,
    }
    return render(request, 'core/store_locations.html', context)

def promotions(request):
    active_promotions = Promotion.objects.filter(is_active=True)
    context = {
        'promotions': active_promotions,
    }
    return render(request, 'core/promotions.html', context)

# API Views
class WishlistAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        serializer = WishlistSerializer(wishlist)
        return Response(serializer.data)
    
    def post(self, request):
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        if product in wishlist.products.all():
            wishlist.products.remove(product)
            message = 'Product removed from wishlist'
        else:
            wishlist.products.add(product)
            message = 'Product added to wishlist'
        
        return Response({
            'success': True,
            'message': message,
            'wishlist': WishlistSerializer(wishlist).data
        })

class NewsletterSubscriberAPI(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    permission_classes = [permissions.AllowAny]

class ContactMessageAPI(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]

class PromotionListAPI(generics.ListAPIView):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer
    permission_classes = [permissions.AllowAny]

class StoreLocationListAPI(generics.ListAPIView):
    queryset = StoreLocation.objects.filter(is_active=True)
    serializer_class = StoreLocationSerializer
    permission_classes = [permissions.AllowAny]

@csrf_protect
@require_POST
def log_javascript_error(request):
    try:
        error_data = json.loads(request.body)
        logger.error(
            'JavaScript Error: %s\nFile: %s\nLine: %s\nColumn: %s\nStack: %s',
            error_data.get('message'),
            error_data.get('filename'),
            error_data.get('lineno'),
            error_data.get('colno'),
            error_data.get('error')
        )
        return JsonResponse({'status': 'logged'})
    except Exception as e:
        logger.error('Error logging JavaScript error: %s', str(e))
        return JsonResponse({'status': 'error'}, status=500)

def custom_404(request, exception):
    return render(request, 'core/errors/404.html', status=404)

def custom_500(request):
    return render(request, 'core/errors/500.html', status=500)