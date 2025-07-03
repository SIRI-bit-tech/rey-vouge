from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderItem, Cart, CartItem, Payment
from .serializers import (
    OrderSerializer, CartSerializer, AddToCartSerializer,
    UpdateCartItemSerializer
)
from products.models import Product
from django.core.mail import send_mail
from django.template.loader import render_to_string
import urllib.parse
import json
from django.views.decorators.http import require_POST, require_GET
from django.contrib.sites.shortcuts import get_current_site
import base64
import os
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from .paystack import PaystackAPI

import hmac
import hashlib

@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    context = {
        'cart': cart,
    }
    return render(request, 'orders/cart.html', context)

@require_POST
@login_required
def cart_add(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Get quantity from request, default to 1
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))
            size = data.get('size')
            color = data.get('color')
        else:
            quantity = int(request.POST.get('quantity', 1))
            size = request.POST.get('size')
            color = request.POST.get('color')
        
        # Use first available size and color if not provided
        if not size and product.available_sizes:
            size = product.available_sizes[0]
        if not color and product.colors:
            color = product.colors[0]
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if product already exists in cart with same size and color
        cart_item = CartItem.objects.filter(
            cart=cart,
            product=product,
            size=size,
            color=color
        ).first()
        
        if cart_item:
            cart_item.quantity += quantity
            cart_item.save()
        else:
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                size=size,
                color=color
            )
        
        cart_count = cart.get_total_items()
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'message': 'Added to cart'
        })
        
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid request'
        }, status=400)
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

@require_POST
@login_required
def cart_remove(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        
        cart = request.user.cart
        cart_count = cart.get_total_items()
        cart_total = cart.total
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count,
            'cart_total': float(cart_total),
            'message': 'Item removed from cart'
        })
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Item not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@require_POST
@login_required
def cart_update(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))
        else:
            quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        
        cart = request.user.cart
        cart_count = cart.get_total_items()
        cart_total = cart.total
        item_total = cart_item.get_total_price() if quantity > 0 else 0
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'cart_count': cart_count,
            'cart_total': float(cart_total),
            'item_total': float(item_total)
        })
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid quantity'
        }, status=400)
    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Item not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def checkout(request):
    cart = Cart.objects.get_or_create(user=request.user)[0]
    
    if request.method == 'POST':
        # Validate shipping address
        shipping_data = {
            'full_name': request.POST.get('full_name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
            'city': request.POST.get('city'),
            'state': request.POST.get('state'),
            'postal_code': request.POST.get('postal_code'),
        }
        
        # Store shipping data in cart
        cart.shipping_address = shipping_data
        cart.save()
        
        return redirect('orders:checkout_review')
    
    context = {
        'cart': cart,
        'step': 1,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    }
    return render(request, 'orders/checkout.html', context)

@login_required
def checkout_shipping(request):
    if request.method == 'POST':
        # Process shipping information
        shipping_data = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'email': request.POST.get('email'),
            'phone_number': request.POST.get('phone_number'),
            'address': request.POST.get('address'),
            'city': request.POST.get('city'),
            'state': request.POST.get('state'),
            'country': request.POST.get('country'),
            'postal_code': request.POST.get('postal_code'),
        }
        
        cart = request.user.cart
        cart.shipping_address = shipping_data
        cart.save()
        
        context = {
            'cart': cart,
            'shipping': shipping_data,
            'step': 2,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
        }
        return render(request, 'orders/checkout.html', context)
    
    return redirect('orders:checkout')

def get_logo_base64():
    try:
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.jpg')
        with open(logo_path, 'rb') as img_file:
            return 'data:image/jpeg;base64,' + base64.b64encode(img_file.read()).decode()
    except Exception:
        return ''

@login_required
@require_POST
def place_order(request):
    try:
        cart = request.user.cart
        if not cart or not cart.items.exists():
            return JsonResponse({
                'success': False,
                'error': 'Cart is empty'
            }, status=400)

        if not cart.shipping_address:
            return JsonResponse({
                'success': False,
                'error': 'Shipping address is required'
            }, status=400)

        shipping = cart.shipping_address
        
        try:
            # Calculate totals
            subtotal = cart.subtotal
            shipping_cost = cart.shipping_cost
            total_amount = cart.total
            
            # Create order in database first
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping,  # Pass the shipping dict directly
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                total_amount=total_amount
            )
        except Exception as order_error:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create order'
            }, status=500)

        try:
            # Create order items
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.get_price(),  # Use get_price() to get sale price if available
                    size=item.size,
                    color=item.color
                )
        except Exception as item_error:
            # Clean up the order if items creation fails
            order.delete()
            return JsonResponse({
                'success': False,
                'error': 'Failed to create order items'
            }, status=500)

        try:
            # Initialize PayStack payment
            paystack = PaystackAPI()
            callback_url = request.build_absolute_uri(reverse('orders:payment_callback'))
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                amount=total_amount
            )
            
            # Initialize payment with PayStack
            response = paystack.initialize_payment(
                email=shipping['email'],
                amount=total_amount,
                reference=payment.reference,
                callback_url=callback_url,
                metadata={
                    'order_number': order.order_number,
                    'payment_id': payment.id
                }
            )
            
            if response.get('status'):
                # Return the payment URL and reference
                return JsonResponse({
                    'success': True,
                    'payment_reference': payment.reference,
                    'order_number': order.order_number
                })
            else:
                # If payment initialization fails, delete the order and payment
                payment.delete()
                order.delete()
                return JsonResponse({
                    'success': False,
                    'error': 'Payment initialization failed'
                }, status=500)

        except Exception as payment_error:
            # Clean up if payment initialization fails
            order.delete()
            return JsonResponse({
                'success': False,
                'error': 'Failed to initialize payment'
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def checkout_complete(request):
    order = Order.objects.filter(user=request.user).latest('created_at')
    context = {
        'order': order,
    }
    return render(request, 'orders/checkout_complete.html', context)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user)
    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_list.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)

# API Views
class CartAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']
            size = serializer.validated_data['size']
            color = serializer.validated_data['color']
            
            product = get_object_or_404(Product, id=product_id)
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                color=color,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            return Response({
                'success': True,
                'message': 'Product added to cart',
                'cart': CartSerializer(cart).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderListAPI(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class OrderDetailAPI(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

@csrf_exempt
def payment_webhook(request):
    """Handle PayStack webhook"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    # Verify webhook signature
    paystack_signature = request.headers.get('x-paystack-signature')
    if not paystack_signature:
        return JsonResponse({'status': 'error', 'message': 'No signature found'})
    
    # Compute expected signature
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        request.body,
        hashlib.sha512
    ).hexdigest()
    
    if paystack_signature != computed_signature:
        return JsonResponse({'status': 'error', 'message': 'Invalid signature'})
    
    # Process the webhook
    payload = json.loads(request.body)
    event = payload.get('event')
    data = payload.get('data', {})
    
    if event == 'charge.success':
        reference = data.get('reference')
        payment = get_object_or_404(Payment, reference=reference)
        
        # Update payment status
        payment.status = 'success'
        payment.paystack_reference = data.get('id')
        payment.save()
        
        # Update order status
        order = payment.order
        order.mark_as_paid(
            payment_reference=reference,
            payment_method='paystack'
        )
        
        # Send confirmation email
        context = {
            'order': order,
            'items': order.items.all(),
        }
        html_message = render_to_string('orders/email/order_confirmation.html', context)
        send_mail(
            subject=f'Order Confirmation - {order.order_number}',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            html_message=html_message
        )
    
    return JsonResponse({'status': 'success'})

@login_required
def payment_callback(request):
    """Handle PayStack payment callback"""
    reference = request.GET.get('reference')
    if not reference:
        messages.error(request, 'No payment reference found')
        return redirect('orders:cart')
    
    payment = get_object_or_404(Payment, reference=reference)
    paystack = PaystackAPI()
    
    # Verify payment
    response = paystack.verify_payment(reference)
    
    if response.get('status') and response.get('data', {}).get('status') == 'success':
        # Payment successful
        payment.status = 'success'
        payment.paystack_reference = response['data']['id']
        payment.save()
        
        # Update order status
        order = payment.order
        order.mark_as_paid(
            payment_reference=reference,
            payment_method='paystack'
        )
        
        messages.success(request, 'Payment successful! Your order has been confirmed.')
        return redirect('orders:order_confirmation', order_number=order.order_number)
    else:
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('orders:cart')

@login_required
def order_confirmation(request, order_number):
    """Display order confirmation page"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/order_confirmation.html', {'order': order})
