from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class CustomUser(AbstractUser):
    username = None  # Remove username field completely
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    
    # Profile fields
    bio = models.TextField(_('biography'), blank=True)
    birth_date = models.DateField(_('birth date'), null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(_('email notifications'), default=True)
    newsletter_subscription = models.BooleanField(_('newsletter subscription'), default=True)
    
    # Premium features
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)
    
    # Social links
    facebook_profile = models.URLField(max_length=255, blank=True)
    instagram_profile = models.URLField(max_length=255, blank=True)
    twitter_profile = models.URLField(max_length=255, blank=True)
    
    # Account status
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    last_updated = models.DateTimeField(_('last updated'), auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def is_premium_active(self):
        if not self.is_premium:
            return False
        if not self.premium_expiry:
            return False
        return timezone.now() <= self.premium_expiry
    
    def save(self, *args, **kwargs):
        self.last_updated = timezone.now()
        super().save(*args, **kwargs)
