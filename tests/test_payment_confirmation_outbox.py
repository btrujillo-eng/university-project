from types import SimpleNamespace

from pydantic import SecretStr

from app.infrastructure.notifications.payment_confirmation_worker import (
    PaymentConfirmationOutboxWorker,
)


def test_confirmation_email_escapes_untrusted_html(monkeypatch) -> None:
    sent = {}
    monkeypatch.setattr(
        "app.infrastructure.notifications.payment_confirmation_worker.resend.Emails.send",
        lambda payload: sent.update(payload),
    )
    settings = SimpleNamespace(
        resend_api_key=SecretStr("test-api-key"),
        resend_from_email="sender@example.com",
    )
    worker = PaymentConfirmationOutboxWorker(session_factory=None, settings=settings)

    worker._send_email(
        {
            "email": "customer@example.com",
            "first_name": "<script>alert(1)</script>",
            "transaction_id": "txn_123",
            "amount": "100.00",
            "currency": "cop",
            "created_at": "2026-10-28T10:00:00+00:00",
            "processing_network": "Visa",
            "last_digits": "4242",
        }
    )

    assert sent["to"] == ["customer@example.com"]
    assert sent["from"] == "sender@example.com"
    assert "&lt;script&gt;" in sent["html"]
    assert "<script>" not in sent["html"]
    assert sent["subject"] == "Confirmación de pago txn_123"
