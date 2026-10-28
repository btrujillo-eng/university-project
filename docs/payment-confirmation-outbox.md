# Durable card-payment confirmation emails

Successful card payments are inserted into the PostgreSQL `outbox_events` table. The API response is based on the payment processor result; a Resend outage does not turn an already-approved charge into a failed payment.

## Setup

1. Configure `RESEND_API_KEY` and `RESEND_FROM_EMAIL` in the environment. The sender defaults to Resend's test sender `onboarding@resend.dev`; production sending requires a verified sender/domain in Resend.
2. Apply the database migration with the migration role: `alembic upgrade head`.
3. Start the FastAPI application normally. Its lifespan starts the polling worker.
4. Inspect `outbox_events`: `pending` means waiting for retry, `processing` means claimed by a worker, `sent` means delivered to Resend, and `failed` means retry attempts were exhausted.

## Delivery semantics

- A unique event key prevents the same transaction confirmation from being queued more than once.
- The worker uses PostgreSQL row locks with `SKIP LOCKED`, expiring leases, exponential retry delays, and a bounded retry count.
- A process crash after Resend accepts an email but before the database records `sent` can cause a duplicate email. This is at-least-once delivery, not exactly-once delivery.
- The outbox row is persisted immediately after the processor returns success. Because the payment provider and PostgreSQL do not share a distributed transaction, a database outage at that moment can still leave a successful charge without a queued email. The code logs this as a critical operational failure; reconciliation/webhooks are the next hardening step.
- This worker is suitable for a single application deployment or multiple replicas using the shared PostgreSQL database. Configure the database migration before deploying the code.
