from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import NewsletterSubscriber
from .utils import send_email, send_bulk_email

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': settings.EMAIL_TASK_MAX_RETRIES}
)
def send_welcome_email(self, subscriber_id):
    """Send welcome email to new newsletter subscribers."""
    try:
        subscriber = NewsletterSubscriber.objects.get(id=subscriber_id)
        context = {
            'subscriber': subscriber,
            'subscriber_name': subscriber.name or subscriber.email,
            'site_url': settings.SITE_URL,
            'logo_url': f"{settings.SITE_URL}/static/images/logo.jpg",
            'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{subscriber.unsubscribe_token}/",
        }
        
        send_email(
            subject='Welcome to Rey Premium Vogue Newsletter!',
            template_name='core/emails/newsletter_welcome.html',
            to_email=subscriber.email,
            to_name=subscriber.name or subscriber.email,
            context=context
        )
        
        subscriber.welcome_email_sent = True
        subscriber.save()
        
    except Exception as e:
        self.retry(exc=e)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': settings.EMAIL_TASK_MAX_RETRIES}
)
def send_newsletter(self, subject, template_name, context, subscriber_ids=None):
    """Send newsletter to subscribers."""
    try:
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)
        if subscriber_ids:
            subscribers = subscribers.filter(id__in=subscriber_ids)
        
        base_context = {
            'site_url': settings.SITE_URL,
            'logo_url': f"{settings.SITE_URL}/static/images/logo.jpg",
        }
        base_context.update(context)
        
        # Prepare recipients data
        recipients = [
            {
                'email': subscriber.email,
                'name': subscriber.name or subscriber.email,
            }
            for subscriber in subscribers
        ]
        
        send_bulk_email(
            subject=subject,
            template_name=template_name,
            recipients=recipients,
            context=base_context
        )
            
    except Exception as e:
        self.retry(exc=e)

@shared_task
def process_inactive_subscribers():
    """Process subscribers who haven't opened emails in a while."""
    cutoff_date = timezone.now() - timedelta(days=90)  # 3 months
    inactive_subscribers = NewsletterSubscriber.objects.filter(
        is_active=True,
        last_opened_at__lt=cutoff_date
    )
    
    for subscriber in inactive_subscribers:
        send_reactivation_email.delay(subscriber.id)
        subscriber.reactivation_email_sent = True
        subscriber.save()

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': settings.EMAIL_TASK_MAX_RETRIES}
)
def send_reactivation_email(self, subscriber_id):
    """Send reactivation email to inactive subscribers."""
    try:
        subscriber = NewsletterSubscriber.objects.get(id=subscriber_id)
        context = {
            'subscriber': subscriber,
            'subscriber_name': subscriber.name or subscriber.email,
            'site_url': settings.SITE_URL,
            'logo_url': f"{settings.SITE_URL}/static/images/logo.jpg",
            'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{subscriber.unsubscribe_token}/",
            'reactivate_url': f"{settings.SITE_URL}/newsletter/reactivate/{subscriber.unsubscribe_token}/",
        }
        
        send_email(
            subject='We Miss You! - Rey Premium Vogue Newsletter',
            template_name='core/emails/newsletter_reactivation.html',
            to_email=subscriber.email,
            to_name=subscriber.name or subscriber.email,
            context=context
        )
        
    except Exception as e:
        self.retry(exc=e)