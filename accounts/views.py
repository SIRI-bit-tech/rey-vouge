from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from orders.models import Order
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from .serializers import (
    UserSerializer, UserProfileUpdateSerializer,
    ChangePasswordSerializer
)
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, View
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, send_mail
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from products.models import Product
from core.models import Wishlist

User = get_user_model()

def generate_token(user):
    return default_token_generator.make_token(user)

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    context = {
        'user': request.user,
        'recent_orders': orders,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_edit(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.bio = request.POST.get('bio', '')
        
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']
        
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    
    return redirect('accounts:profile')

@login_required
def update_preferences(request):
    if request.method == 'POST':
        user = request.user
        user.email_notifications = request.POST.get('email_notifications') == 'on'
        user.newsletter_subscription = request.POST.get('newsletter_subscription') == 'on'
        user.save()
        messages.success(request, 'Preferences updated successfully.')
    
    return redirect('accounts:profile')

@login_required
def update_social_links(request):
    if request.method == 'POST':
        user = request.user
        user.facebook_profile = request.POST.get('facebook_profile', '')
        user.instagram_profile = request.POST.get('instagram_profile', '')
        user.twitter_profile = request.POST.get('twitter_profile', '')
        user.save()
        messages.success(request, 'Social links updated successfully.')
    
    return redirect('accounts:profile')

@login_required
def change_password(request):
    if request.method == 'POST':
        user = request.user
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:login')
    
    return render(request, 'accounts/change_password.html')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'accounts/order_history.html', context)

@login_required
def wishlist(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    context = {
        'wishlist': wishlist,
    }
    return render(request, 'accounts/wishlist.html', context)

@require_POST
@login_required
def add_to_wishlist(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        if product in wishlist.products.all():
            wishlist.products.remove(product)
            return JsonResponse({
                'success': True,
                'added': False,
                'wishlist_count': wishlist.products.count()
            })
            
        wishlist.products.add(product)
        return JsonResponse({
            'success': True,
            'added': True,
            'wishlist_count': wishlist.products.count()
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@require_GET
def get_wishlist_count(request):
    if request.user.is_authenticated:
        count = request.user.wishlist.products.count() if hasattr(request.user, 'wishlist') else 0
        return JsonResponse({'success': True, 'wishlist_count': count})
    return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)

@login_required
def toggle_wishlist_privacy(request):
    """Toggle the privacy setting of a user's wishlist"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
        
    try:
        wishlist = request.user.wishlist
        is_public = wishlist.toggle_privacy()
        
        return JsonResponse({
            'success': True,
            'is_public': is_public
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

def shared_wishlist(request, share_id):
    """View a shared wishlist"""
    wishlist = get_object_or_404(Wishlist, share_id=share_id)
    
    if not wishlist.is_public and request.user != wishlist.user:
        return render(request, '404.html', status=404)
    
    context = {
        'wishlist': wishlist,
        'is_owner': request.user == wishlist.user
    }
    return render(request, 'accounts/shared_wishlist.html', context)

# API Views
class ProfileAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': UserSerializer(request.user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({
                    'success': True,
                    'message': 'Password changed successfully'
                })
            return Response({
                'success': False,
                'message': 'Incorrect old password'
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            # Session expires when browser closes
            self.request.session.set_expiry(0)
        else:
            # Session expires in 2 weeks
            self.request.session.set_expiry(1209600)

        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('core:home')

class RegisterView(View):
    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Welcome to REY PREMIUM VOGUE!')
            return redirect('core:home')
        return render(request, 'accounts/register.html', {'form': form})
