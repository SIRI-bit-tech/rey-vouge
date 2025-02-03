from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from core.models import Wishlist

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wishlist(sender, instance, created, **kwargs):
    if created:
        Wishlist.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_wishlist(sender, instance, **kwargs):
    if not hasattr(instance, 'wishlist'):
        Wishlist.objects.create(user=instance) 