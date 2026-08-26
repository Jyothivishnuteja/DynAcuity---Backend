from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
import requests
import logging
import os

logger = logging.getLogger(__name__)

class HybridEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.smtp_backend = SmtpEmailBackend(fail_silently=fail_silently, **kwargs)

    def send_messages(self, email_messages):
        api_key = os.getenv("RESEND_API_KEY")
        
        # If RESEND_API_KEY is configured, use Resend HTTP API
        if api_key:
            logger.info("Using Resend API to send emails...")
            return self.send_messages_via_resend(email_messages, api_key)
        
        # Otherwise, fall back to standard SMTP (Gmail)
        logger.info("RESEND_API_KEY not found. Falling back to Gmail SMTP...")
        return self.smtp_backend.send_messages(email_messages)

    def send_messages_via_resend(self, email_messages, api_key):
        if not email_messages:
            return 0

        sent_count = 0
        from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

        for message in email_messages:
            try:
                # Prepare payload
                payload = {
                    "from": from_email,
                    "to": message.to,
                    "subject": message.subject,
                    "text": message.body,
                }
                
                # Check for HTML alternative content
                if hasattr(message, 'alternatives') and message.alternatives:
                    for alt in message.alternatives:
                        if alt[1] == 'text/html':
                            payload['html'] = alt[0]
                            break

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                
                response = requests.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers=headers,
                    timeout=5,
                )
                
                if response.status_code in (200, 201, 202):
                    sent_count += 1
                else:
                    logger.error(f"Resend API error: {response.status_code} - {response.text}")
                    raise Exception(f"Resend API failed with status {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"Failed to send email via Resend: {str(e)}", exc_info=True)
                if not self.fail_silently:
                    raise

        return sent_count
