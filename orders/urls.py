from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Cart URLs
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    
    # Checkout URLs
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/shipping/', views.checkout_shipping, name='checkout_shipping'),
    path('checkout/complete/', views.checkout_complete, name='checkout_complete'),
    path('place-order/', views.place_order, name='place_order'),
    
    # Order URLs
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # API URLs
    path('api/cart/', views.CartAPI.as_view(), name='cart_api'),
    path('api/orders/', views.OrderListAPI.as_view(), name='order_list_api'),
    path('api/orders/<int:pk>/', views.OrderDetailAPI.as_view(), name='order_detail_api'),

    # Payment URLs
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/webhook/', views.payment_webhook, name='payment_webhook'),
    path('order/confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),
] 