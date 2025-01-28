from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderItem, Cart, CartItem
from .serializers import (
    OrderSerializer, CartSerializer, AddToCartSerializer,
    UpdateCartItemSerializer
)
from products.models import Product
from django.core.mail import send_mail
from django.template.loader import render_to_string
import urllib.parse
import json
from django.views.decorators.http import require_POST

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
    cart = request.user.cart
    context = {
        'cart': cart,
        'step': 1,
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
        }
        return render(request, 'orders/checkout.html', context)
    
    return redirect('orders:checkout')

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
            print(f"Order creation failed: {str(order_error)}")
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
            print(f"Order items creation failed: {str(item_error)}")
            # Clean up the order if items creation fails
            order.delete()
            return JsonResponse({
                'success': False,
                'error': 'Failed to create order items'
            }, status=500)

        try:
            # Prepare order details for WhatsApp
            order_items = []
            for item in cart.items.all():
                product_url = request.build_absolute_uri(f'/products/{item.product.slug}/')
                item_total = item.quantity * item.product.get_price()  # Calculate total price
                order_items.append(
                    f"• {item.product.name}\n  Size: {item.size}\n  Color: {item.color}\n  Quantity: {item.quantity}\n  Price: ₦{item_total}\n  Link: {product_url}"
                )

            order_details = "\n\n".join(order_items)
            shipping_address = f"{shipping.get('address', '')}, {shipping.get('city', '')}, {shipping.get('state', '')}, {shipping.get('country', '')} {shipping.get('postal_code', '')}"
            
            whatsapp_message = f"""*New Order from REY PREMIUM VOGUE*

*Customer Details:*
Name: {shipping.get('first_name', '')} {shipping.get('last_name', '')}
Email: {shipping.get('email', '')}
Phone: {shipping.get('phone_number', '')}
Shipping Address: {shipping_address}

*Order Details:*
{order_details}

*Order Summary:*
Subtotal: ₦{subtotal}
Shipping: ₦{shipping_cost}
Total: ₦{total_amount}

Order ID: #{order.id}"""

            # Create WhatsApp URL
            whatsapp_number = getattr(settings, 'ADMIN_WHATSAPP', '')
            if not whatsapp_number:
                whatsapp_number = '1234567890'  # Fallback number if not set
            whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(whatsapp_message)}"

        except Exception as whatsapp_error:
            print(f"WhatsApp message preparation failed: {str(whatsapp_error)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to prepare WhatsApp message'
            }, status=500)

        try:
            # Send email to customer
            customer_subject = f"Order Confirmation - REY PREMIUM VOGUE #{order.id}"
            customer_message = render_to_string('orders/email/order_confirmation.html', {
                'user': request.user,
                'cart': cart,
                'shipping': shipping,
                'site_url': request.build_absolute_uri('/'),
                'order': order,
            })
            send_mail(
                customer_subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [shipping.get('email', '')],
                html_message=customer_message,
                fail_silently=True,
            )

            # Send email to admin
            admin_email = getattr(settings, 'ADMIN_EMAIL', '')
            if admin_email:
                admin_subject = f"New Order #{order.id} from {shipping.get('first_name', '')} {shipping.get('last_name', '')}"
                admin_message = render_to_string('orders/email/admin_notification.html', {
                    'user': request.user,
                    'cart': cart,
                    'shipping': shipping,
                    'site_url': request.build_absolute_uri('/'),
                    'order': order,
                })
                send_mail(
                    admin_subject,
                    '',
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_email],
                    html_message=admin_message,
                    fail_silently=True,
                )
        except Exception as email_error:
            # Log the email error but don't fail the order
            print(f"Email sending failed: {str(email_error)}")

        try:
            # Clear the cart after successful order creation
            cart.items.all().delete()
        except Exception as cart_error:
            print(f"Cart clearing failed: {str(cart_error)}")
            # Don't fail the order if cart clearing fails
        
        return JsonResponse({
            'success': True,
            'whatsapp_url': whatsapp_url,
            'order_id': order.id
        })
        
    except Exception as e:
        # Log the error for debugging
        print(f"Order creation failed with error: {str(e)}")
        import traceback
        traceback.print_exc()  # Print the full traceback
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
