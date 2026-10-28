import os

_TEST_ENV = {
    "STRIPE_API_KEY": "sk_test_placeholder",
    "RESEND_API_KEY": "re_test_placeholder",
    "MIGRATOR_DB_URL": "postgresql://test:test@localhost/test",
    "DB_USER": "test",
    "DB_PASSWORD": "test",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "test",
    "JWT_SECRET_KEY": "test-secret-for-unit-tests-only",
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
}
for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)
