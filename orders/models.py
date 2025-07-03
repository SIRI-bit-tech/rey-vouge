from django.db import models
from django.conf import settings
from products.models import Product
from decimal import Decimal
import uuid
from django.utils import timezone

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Shipping Information
    shipping_address = models.JSONField()
    
    # Order Totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tracking Information
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    
    # Payment Information
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Order {self.order_number} - {self.user.email}'
        
    def save(self, *args, **kwargs):
        # Generate order number if not exists
        if not self.order_number:
            year = str(self.created_at.year)[2:] if self.created_at else str(timezone.now().year)[2:]
            self.order_number = f'REY{year}{str(uuid.uuid4().int)[:6]}'
            
        # Calculate total amount before saving
        self.total_amount = self.subtotal + self.shipping_cost
        super().save(*args, **kwargs)

    def mark_as_paid(self, payment_reference, payment_method):
        self.payment_status = 'paid'
        self.status = 'processing'
        self.payment_reference = payment_reference
        self.payment_method = payment_method
        self.payment_date = timezone.now()
        self.save()
        
        # Reduce product stock
        for item in self.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save()

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

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=200, unique=True)
    paystack_reference = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Payment {self.reference} for Order {self.order.order_number}'
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f'PAY-{str(uuid.uuid4().hex)[:10].upper()}'
        super().save(*args, **kwargs)
