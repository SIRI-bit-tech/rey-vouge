from rest_framework import serializers
from django.contrib.auth import get_user_model
from orders.serializers import OrderSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    orders = OrderSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'full_name', 'phone_number',
            'address', 'city', 'state', 'country', 'postal_code',
            'is_premium', 'premium_expiry', 'orders'
        ]
        read_only_fields = ['email', 'is_premium', 'premium_expiry']
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number',
            'address', 'city', 'state', 'country', 'postal_code'
        ]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return data 