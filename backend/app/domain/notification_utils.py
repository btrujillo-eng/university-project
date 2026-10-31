import logging
from collections import deque

from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.ports import INotificationChannel
from app.domain.strategies import get_notification_method
from app.exceptions import NotificationMethodNotFoundError

logger = logging.getLogger(__name__)
    
def dequeue(
        notifiers_queue: deque[tuple[INotificationChannel, int]], 
        payment_response: PaymentResponse,
        payment_data: PaymentDataRequest
    ) -> list[INotificationChannel]:
    """
    It is responsible for emptying the notification channel queue
    """
    # A list is compiled of the channels where the notifiers failed
    notifiers_failed: list[INotificationChannel] = []
        
    while notifiers_queue:
        notifier, attempts = notifiers_queue.popleft()
        notification_method = get_notification_method(payment_response.payment_status, notifier)
            
        if not notification_method:
            logger.critical("Notification method was found for the notification channels")
            raise NotificationMethodNotFoundError("No notification method was found for the notification channels")
            
        if notification_method(payment_data, payment_response):
            logger.info(f"Notification success with {notifier}")
        else:
            new_attempts = attempts + 1
            if new_attempts < 3:
                notifiers_queue.append((notifier, new_attempts))
            else:
                notifiers_failed.append(notifier)
        
    return notifiers_failed