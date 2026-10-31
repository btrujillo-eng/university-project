import asyncio
import logging

import resend

from app.domain.ports import IRestoreCodeNotifier
from app.exceptions import NotificationServiceError
from app.infrastructure.config import Settings

logger = logging.getLogger(__name__)


class ResendRestoreCodeNotifier(IRestoreCodeNotifier):
    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.resend_api_key.get_secret_value()

    async def send_restore_code(self, email: str, code: str) -> None:
        def send() -> object:
            resend.api_key = self.api_key
            return resend.Emails.send(
                {
                    "from": "onboarding@resend.dev",
                    "to": [email],
                    "subject": "Código para restaurar tu contraseña",
                    "html": (
                        "<h2>Restauración de contraseña</h2>"
                        "<p>Ingresa este código de verificación en el sistema:</p>"
                        f"<p style='font-size: 24px'><strong>{code}</strong></p>"
                        "<p>El código vence en 10 minutos. Si no solicitaste este "
                        "cambio, ignora este correo.</p>"
                    ),
                }
            )
        try:
            await asyncio.to_thread(send)
        except Exception as exc:
            logger.exception("Could not send password-restoration email")
            raise NotificationServiceError(
                "Password-restoration email could not be sent"
            ) from exc
