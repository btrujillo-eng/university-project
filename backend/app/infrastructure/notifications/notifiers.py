import logging
import os

import resend
from dotenv import load_dotenv
from twilio.rest import Client

from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.ports import INotificationChannel
from app.infrastructure.notifications.template import (
    EmailChannelTemplate,
    PhoneChannelTemplate,
)

_ = load_dotenv()

logger = logging.getLogger(__name__)

class WhatsappChannel(INotificationChannel):
    """
    This is the WhatsApp Channel.
    
    It's responsible for sending WhatsApp notifications to user regarding payment details. Any class that 
    implement this channel can define the'notify_successful_payment' and 'notify_failed_payment' methods.
    """
    def __init__(self, whatsapp_channel_template: PhoneChannelTemplate):
        self.whatsapp_channel_template = whatsapp_channel_template
        self.client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.from_ = f"whatsapp:{os.getenv('TWILIO_PHONE')}"
        
    async def notify_successful_payment( self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool:
        """
        Sends a notifications to the user via WhatsApp when the payment
        has been successfully completed.
        """
        if payment_data.user_data.contact_info.phone_number:
            try:
                self.client.messages.create(
                    from_=self.from_,
                    to=f"whatsapp:+57{payment_data.user_data.contact_info.phone_number}",
                    body=self.whatsapp_channel_template.successful_payment_template(payment_data, payment_response)
                )
                logger.info(f"[WhatsAppChannel] The transaction with ID {payment_response.transaction_id} was succesfully notified.")
            except Exception as e:
                logger.critical(f"[WhatsappChannel] is not responding | error: {e}", exc_info=True)
                return False
            
        logger.info(
            f"""
            [WhatsappChannel] The user could not be notified because they did not register
             a phone number to notify them of the payment details with TRANSACTION ID {payment_response.transaction_id}.
            """
        )
        return True

    async def notify_failed_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool:
        """
        Sends a notifications to user via WhatsApp when the payment has been
        rejected.
        """
        if payment_data.user_data.contact_info.phone_number:
            try:
                self.client.messages.create(
                    from_=self.from_,
                    to=f"whatsapp:+57{payment_data.user_data.contact_info.phone_number}",
                    body=self.whatsapp_channel_template.failed_payment_template(payment_data, payment_response)
                )
                logger.info(f"[WhatsAppChannel] The information about TRANSACTION ID {payment_response.transaction_id} was sent succesfully.")
            except Exception as e:
                logger.critical(f"[WhatsappChannel | Failed] is not responding | error: {e}", exc_info=True)
                return False
            
        logger.info(
            f"""
            [WhatsappChannel] The user could not be notified because they did not register
             a phone number to notify them of the payment details with TRANSACTION ID {payment_response.transaction_id}.
            """
        )
        return True

class SmsChannel(INotificationChannel):
    """
    This is the SMS Channel.
    
    It's responsible for sending SMS notifications to user regarding payment details. Any class that implement
    this channel can define the 'notify_successful_payment' and ' notify_failed_payment' methods.
    """
    def __init__(self, sms_channel_template: PhoneChannelTemplate):
        self.sms_channel_template = sms_channel_template
        self.client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.from_ = os.getenv("TWILIO_PHONE")
        
    async def notify_successful_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool:
        """
        Sends a notifications to user via SMS when the payment has
        been successfully completed.
        """
        if payment_data.user_data.contact_info.phone_number:
            try:
                self.client.messages.create(
                    from_=self.from_,
                    to=f"+57{payment_data.user_data.contact_info.phone_number}",
                    body=self.sms_channel_template.successful_payment_template(payment_data, payment_response)
                )
                logger.info(f"[SmsChannel] The information about TRANSACTION ID {payment_response.transaction_id} was sent successfully.")
            except Exception as e:
                logger.critical(f"[SmsChannel] is not responding | error: {e}", exc_info=True)
                return False
            
        logger.info(
            f"""
            [SmsChannel] The user could not be notified because they did not register
             a phone number to notify them of the payment details with TRANSACTION ID {payment_response.transaction_id}.
            """
        )
        return True

    async def notify_failed_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool:
        """
        Sends a notifications to user via SMS when the payment has been rejected.
        """
        if payment_data.user_data.contact_info.phone_number:
            try:
                self.client.messages.create(
                    from_=self.from_,
                    to=f"+57{payment_data.user_data.contact_info.phone_number}",
                    body=self.sms_channel_template.failed_payment_template(payment_data, payment_response)
                )
                logger.info(f"[SmsChannel] The information about TRANSACTION ID {payment_response.transaction_id} was sent successfully.")
            except Exception as e:
                logger.critical(f"[SmsChannel] is not responding | error: {e}", exc_info=True)
                return False

        logger.info(
            f"""
            [SmsChannel] The user could not be notified because they did not register
             a phone number to notify them of the payment details with TRANSACTION ID {payment_response.transaction_id}.
            """
        )
        return True

class EmailChannel(INotificationChannel):
    """
    This is the Email Channel.
    
    It's responsible for sending email notifications to user regarding payment details. Any class that implement
    this channel can define the 'notify_successful_payment' and ' notify_failed_payment' methods.
    """
    def __init__(self, email_channel_template: EmailChannelTemplate):
        self.email_channel_template = email_channel_template
        self.resend = resend.api_key = os.getenv("RESEND_API_KEY")
        
    async def notify_successful_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool:
        """
        Sends a notifications to the user via email when the payment has
        been successfully completed.
        """
        if payment_data.user_data.contact_info.email:
            try:
                resend.Emails.send({
                    "from": "onboarding@resend.dev",
                    "to": payment_data.user_data.contact_info.email,
                    "subject": "✅ Confirmación de tu compra",
                    "html": self.email_channel_template.successful_payment_template(payment_data, payment_response)
                })
                logger.info(f"[EmailChannel] The information about TRANSACTION ID {payment_response.transaction_id} was sent successfully.")
                return True
            except Exception as e:
                logger.critical(f"[EmailChannel] is not responding | error: {e}", exc_info=True)
                return False
        
        logger.info(
            f"""
            [EmailChannel] The user could not be notified because they did not register
             a phone number to notify them of the payment details with TRANSACTION ID {payment_response.transaction_id}.
            """
        )
        return True
        
    async def notify_failed_payment(self, payment_data: PaymentDataRequest, payment_response: PaymentResponse) -> bool:
        """
        Sends a notifications to the user via email when the payment has been rejected.
        """
        if payment_data.user_data.contact_info.email:
            try:
                resend.Emails.send({
                    "from": "onboarding@resend.dev",
                    "to": payment_data.user_data.contact_info.email,
                    "subject": "❌ Rechazamos tu pago",
                    "html": self.email_channel_template.failed_payment_template(payment_data, payment_response)
                })
                logger.info(f"[EmailChannel] The information about TRANSACTION ID {payment_response.transaction_id} was sent succesfully.")
            except Exception as e:
                logger.critical(f"[EmailChannel] is not responding | error: {e}", exc_info=True)
                return False
        
        return True