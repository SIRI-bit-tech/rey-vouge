from django.conf import settings
from typing import List, Dict, Optional
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail, EmailMultiAlternatives


def send_email(
    subject: str,
    template_name: str,
    to_email: str,
    to_name: str,
    context: Dict,
    attachments: Optional[List[Dict]] = None
):
    """
    Send an email using Django's email functionality
    """
    # Render the template
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    
    # Create email message
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email]
    )
    
    # Attach HTML content
    email.attach_alternative(html_content, "text/html")
    
    # Add attachments if any
    if attachments:
        for attachment in attachments:
            email.attach(
                filename=attachment['filename'],
                content=attachment['content'],
                mimetype=attachment.get('mimetype', 'application/octet-stream')
            )
    
    # Send the email
    return email.send()


def send_bulk_email(
    subject: str,
    template_name: str,
    recipients: List[Dict[str, str]],
    context: Dict,
    batch_size: int = 50
):
    """
    Send the same email to multiple recipients using Django's email functionality
    """
    # Render the template
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    
    # Process recipients in batches
    for i in range(0, len(recipients), batch_size):
        batch = recipients[i:i + batch_size]
        
        # Get email addresses for this batch
        to_emails = [r['email'] for r in batch]
        
        # Create and send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_emails[0]],  # Primary recipient
            bcc=to_emails[1:],  # BCC all other recipients
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        email.send()