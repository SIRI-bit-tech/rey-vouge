from rest_framework import serializers
from .models import Order, OrderItem, Cart, CartItem
from products.serializers import ProductSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'size', 'color', 'get_total_price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'user_email', 'status', 'created_at', 'updated_at',
            'shipping_address', 'subtotal', 'shipping_cost', 'tax_amount',
            'total_amount', 'tracking_number', 'estimated_delivery', 'items'
        ]
        read_only_fields = ['user_email', 'created_at', 'updated_at']
    
    def get_user_email(self, obj):
        return obj.user.email

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'size', 'color', 'total_price']
    
    def get_total_price(self, obj):
        return obj.get_total_price()

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'subtotal', 'shipping_cost', 'tax_amount', 'total']

class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    size = serializers.CharField()
    color = serializers.CharField()

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1) 