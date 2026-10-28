from datetime import datetime

from app.api.schemas.user import Email
from app.domain.events.base import DomainEvent

 
class UserRegistered(DomainEvent):
    firt_name: str
    email: Email
    ocurred_at: datetime
    