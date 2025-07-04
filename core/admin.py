from django.contrib import admin  
from .models import NewsletterSubscriber, ContactMessage  
  
@admin.register(NewsletterSubscriber)  
class NewsletterSubscriberAdmin(admin.ModelAdmin):  
    list_display = ('email', 'is_active', 'created_at')  
    list_filter = ('is_active', 'created_at')  
    search_fields = ('email',)  
    readonly_fields = ('created_at',)  
  
@admin.register(ContactMessage)  
class ContactMessageAdmin(admin.ModelAdmin):  
    list_display = ('name', 'email', 'subject', 'created_at')  
    list_filter = ('created_at',)  
    search_fields = ('name', 'email', 'subject', 'message')  
    readonly_fields = ('created_at',) 
