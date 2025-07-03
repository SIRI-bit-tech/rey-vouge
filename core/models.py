from django.db import models
from django.conf import settings
from products.models import Product
from django.urls import reverse
import uuid
import string
import random
import time
from django.utils import timezone

def generate_unique_share_id():
    """Generate a unique share ID combining timestamp and random characters"""
    timestamp = hex(int(time.time()))[2:]  # Remove '0x' prefix
    random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}-{random_chars}"

class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='wishlist', on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='wishlists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_id = models.CharField(max_length=50, blank=True, null=True)  # Temporarily remove unique=True
    is_public = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Wishlist for {self.user.email}"
        
    def save(self, *args, **kwargs):
        if not self.share_id:
            # Generate a unique share_id
            while True:
                share_id = generate_unique_share_id()
                if not Wishlist.objects.filter(share_id=share_id).exists():
                    self.share_id = share_id
                    break
        super().save(*args, **kwargs)
        
    def get_share_url(self):
        """Get the public sharing URL for this wishlist"""
        if not self.is_public:
            return None
        return reverse('accounts:shared_wishlist', kwargs={'share_id': self.share_id})
        
    def toggle_privacy(self):
        """Toggle the wishlist's privacy setting"""
        self.is_public = not self.is_public
        self.save()
        return self.is_public

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True)
    welcome_email_sent = models.BooleanField(default=False)
    reactivation_email_sent = models.BooleanField(default=False)
    preferences = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'
    
    def __str__(self):
        return self.email
    
    def mark_opened(self):
        self.last_opened_at = timezone.now()
        self.save()
    
    def get_full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email.split('@')[0]
    
    def save(self, *args, **kwargs):
        if not self.unsubscribe_token:
            self.unsubscribe_token = uuid.uuid4()
        super().save(*args, **kwargs)

class ContactMessage(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.name}: {self.subject}"

class Promotion(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    discount_percentage = models.PositiveIntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, related_name='promotions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title
    
    @property
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class StoreLocation(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    opening_hours = models.JSONField()  # Store hours for each day
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.city}"

class ProductView(models.Model):
    """Track product views for recommendations"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=40)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['product', 'timestamp']),
        ]
        
    def __str__(self):
        return f"View of {self.product.name} by {'User' if self.user else 'Anonymous'}"
