from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price', 'size', 'color')
    can_delete = False
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'total_amount', 'tracking_number')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'tracking_number')
    readonly_fields = ('user', 'created_at', 'updated_at', 'subtotal', 'shipping_cost', 'total_amount')
    inlines = [OrderItemInline]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at', 'total')
    search_fields = ('user__email',)
    inlines = [CartItemInline]
