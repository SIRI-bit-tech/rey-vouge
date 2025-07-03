from django.contrib import admin
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from .models import NewsletterSubscriber, ContactMessage

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at', 'get_status')
    list_filter = ('is_active',)
    search_fields = ('email',)
    date_hierarchy = 'created_at'
    actions = ['send_newsletter', 'activate_subscribers', 'deactivate_subscribers']
    readonly_fields = ('created_at',)
    list_per_page = 50

    def get_status(self, obj):
        return 'Active' if obj.is_active else 'Inactive'
    get_status.short_description = 'Status'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-newsletter/', self.send_newsletter_view, name='send-newsletter'),
        ]
        return custom_urls + urls

    def send_newsletter_view(self, request):
        if request.method == 'POST':
            subject = request.POST.get('subject')
            content = request.POST.get('content')
            
            if not subject or not content:
                self.message_user(request, "Both subject and content are required", level=messages.ERROR)
                return HttpResponseRedirect("../")

            # Get selected subscribers from session or all active subscribers
            selected_emails = request.session.get('selected_subscribers')
            if selected_emails:
                subscribers = NewsletterSubscriber.objects.filter(email__in=selected_emails, is_active=True)
                del request.session['selected_subscribers']
            else:
                subscribers = NewsletterSubscriber.objects.filter(is_active=True)
            
            total_subscribers = subscribers.count()
            
            if total_subscribers == 0:
                self.message_user(request, "No active subscribers found", level=messages.WARNING)
                return HttpResponseRedirect("../")

            current_site = get_current_site(request)
            site_url = f"https://{current_site.domain}" if request.is_secure() else f"http://{current_site.domain}"
            
            context = {
                'subject': subject,
                'content': content,
                'site_url': site_url,
                'unsubscribe_url': f"{site_url}/newsletter/unsubscribe/"
            }
            
            html_message = render_to_string('core/emails/newsletter_update.html', context)
            
            # Send emails in batches
            BATCH_SIZE = 50
            successful_sends = 0
            failed_sends = 0
            
            for i in range(0, total_subscribers, BATCH_SIZE):
                batch = subscribers[i:i + BATCH_SIZE]
                recipient_list = [subscriber.email for subscriber in batch]
                
                try:
                    send_mail(
                        subject=f"{subject} - REY PREMIUM VOGUE",
                        message='',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=recipient_list,
                        html_message=html_message
                    )
                    successful_sends += len(recipient_list)
                except Exception as e:
                    failed_sends += len(recipient_list)
                    print(f"Failed to send newsletter batch: {str(e)}")

            message = f"Newsletter sent to {successful_sends} subscribers successfully."
            if failed_sends > 0:
                message += f" Failed to send to {failed_sends} subscribers."
            
            self.message_user(request, message)
            return HttpResponseRedirect("../")

        context = {
            'title': 'Send Newsletter',
            'opts': self.model._meta,
            'has_selected': bool(request.session.get('selected_subscribers')),
            'selected_count': len(request.session.get('selected_subscribers', [])),
        }
        return TemplateResponse(request, 'admin/core/newslettersubscriber/send_newsletter.html', context)

    def send_newsletter(self, request, queryset):
        selected = queryset.values_list('email', flat=True)
        request.session['selected_subscribers'] = list(selected)
        return HttpResponseRedirect("send-newsletter/")
    send_newsletter.short_description = "Send newsletter to selected subscribers"

    def activate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscribers were successfully activated.')
    activate_subscribers.short_description = "Mark selected subscribers as active"

    def deactivate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscribers were successfully deactivated.')
    deactivate_subscribers.short_description = "Mark selected subscribers as inactive"

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
