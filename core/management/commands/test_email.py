from django.core.management.base import BaseCommand
from core.utils import send_email
from django.conf import settings
import smtplib
import ssl

class Command(BaseCommand):
    help = 'Test email sending functionality'

    def add_arguments(self, parser):
        parser.add_argument('to_email', type=str, help='Email address to send test to')

    def handle(self, *args, **options):
        try:
            # Print configuration for debugging
            self.stdout.write("Email Configuration:")
            self.stdout.write(f"Using email: {settings.EMAIL_HOST_USER}")
            self.stdout.write(f"Password length: {len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 0}")
            
            # Test SMTP connection first
            self.stdout.write("Testing SMTP connection...")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context) as server:
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                self.stdout.write(self.style.SUCCESS("SMTP connection successful!"))
            
            # Send test email
            self.stdout.write("Sending test email...")
            response = send_email(
                subject="Test Email from Rey Vogue",
                template_name="core/email/test_email.html",
                to_email=options['to_email'],
                to_name="Test User",
                context={
                    "title": "Test Email",
                    "content": "This is a test email from Rey Vogue"
                }
            )
            
            self.stdout.write(self.style.SUCCESS('Email sent successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed: {str(e)}')) 