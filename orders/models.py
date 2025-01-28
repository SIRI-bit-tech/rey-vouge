from django.db import models
from django.conf import settings
from products.models import Product
from decimal import Decimal

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Shipping Information
    shipping_address = models.JSONField()
    
    # Order Totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tracking Information
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Order {self.id} - {self.user.email}'
        
    def save(self, *args, **kwargs):
        # Calculate total amount before saving
        self.total_amount = self.subtotal + self.shipping_cost
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return f'{self.quantity}x {self.product.name} in Order {self.order.id}'
    
    def get_total_price(self):
        return self.price * self.quantity

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipping_address = models.JSONField(null=True, blank=True)
    
    @property
    def subtotal(self):
        return sum(item.get_total_price() for item in self.items.all())
    
    @property
    def shipping_cost(self):
        # Calculate shipping cost based on your business logic
        return Decimal('10.00') if self.subtotal < Decimal('100.00') else Decimal('0.00')
    
    @property
    def total(self):
        return self.subtotal + self.shipping_cost
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    def __str__(self):
        return f'Cart for {self.user.email}'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        unique_together = ('cart', 'product', 'size', 'color')
    
    def __str__(self):
        return f'{self.quantity}x {self.product.name} in {self.cart}'
    
    def get_total_price(self):
        return self.product.get_price() * self.quantity
