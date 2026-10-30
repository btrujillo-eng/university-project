# Durable card-payment confirmation emails

Successful card payments are inserted into the PostgreSQL `outbox_events` table. The API response reflects the payment processor result; a Resend outage does not turn an already-approved charge into a failed payment.

## Setup

1. Configure `RESEND_API_KEY` and `RESEND_FROM_EMAIL`. The sender defaults to Resend's test sender `onboarding@resend.dev`; production sending requires a verified sender/domain in Resend.
2. Apply the database migrations with the migration role: `alembic upgrade head`. The outbox migration is revision `20261030_06`, chained after `20261029_05_fractional_quantities`.
3. Start the FastAPI application. Its lifespan starts the polling worker.
4. Inspect `outbox_events`: `pending` means waiting for processing/retry, `processing` means claimed by a worker, `sent` means Resend accepted the email, and `failed` means retry attempts were exhausted.

## Delivery semantics and limitations

- A unique event key prevents the same transaction confirmation from being enqueued more than once.
- The worker uses PostgreSQL row locks with `SKIP LOCKED`, expiring leases, exponential retry delays, and a bounded retry count. Transient worker/database errors are logged and do not terminate the polling task.
- A process crash after Resend accepts an email but before the database records `sent` can cause a duplicate email. This is at-least-once delivery, not exactly-once delivery.
- The outbox row is persisted after the processor returns success. Stripe and PostgreSQL do not share a distributed transaction, so a database outage at that moment can leave a successful charge without a queued email. The failure is logged; webhook/reconciliation is a future hardening step.
- This worker handles successful card-payment confirmation emails only. Other notification channels and payment outcomes are not migrated by this change.
- Configure the database migration before deploying the application.
