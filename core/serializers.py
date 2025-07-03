from rest_framework import serializers
from .models import Wishlist, NewsletterSubscriber, ContactMessage, Promotion, StoreLocation
from products.serializers import ProductSerializer

class WishlistSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'products', 'created_at', 'updated_at']
        read_only_fields = ['user']

class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'is_active', 'subscribed_at']
        read_only_fields = ['is_active', 'subscribed_at']

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']

class PromotionSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'title', 'description', 'discount_percentage',
            'start_date', 'end_date', 'is_active', 'products',
            'is_valid', 'created_at'
        ]

class StoreLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreLocation
        fields = [
            'id', 'name', 'address', 'city', 'state', 'country',
            'postal_code', 'phone', 'email', 'latitude', 'longitude',
            'opening_hours', 'is_active'
        ] 