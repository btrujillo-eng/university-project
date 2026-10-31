from app.infrastructure.hasher import Hasher


def test_password_hash_is_not_the_plain_text_password() -> None:
    password = "A-strong-password-123"

    password_hash = Hasher().apply_hash(password)

    assert password_hash != password
    assert password_hash.startswith("$2")


def test_password_hash_verifies_only_the_original_password() -> None:
    hasher = Hasher()
    password_hash = hasher.apply_hash("A-strong-password-123")

    assert hasher.check_hash(password_hash, "A-strong-password-123") is True
    assert hasher.check_hash(password_hash, "different-password") is False


def test_password_verification_rejects_malformed_hash() -> None:
    assert Hasher().check_hash("not-a-bcrypt-hash", "any-password") is False
