from sqlalchemy.dialects import postgresql

from app.domain.enums import DeliveryStatus
from app.infrastructure.persistence.repositories.postgresql.order import OrderRepository


class FakeScalarResult:
    def all(self):
        return []


class FakeSession:
    def __init__(self):
        self.statement = None

    async def scalars(self, statement):
        self.statement = statement
        return FakeScalarResult()


def test_customer_order_pagination_uses_stable_tie_breaker():
    session = FakeSession()
    repository = OrderRepository(session)

    import asyncio
    result = asyncio.run(repository.get_customer_orders(user_id=7, limit=10, offset=20))

    compiled = session.statement.compile(dialect=postgresql.dialect())
    assert result == []
    assert "ORDER BY orders.created_at DESC, orders.id DESC" in str(compiled)
    assert compiled.params["param_1"] == 10
    assert compiled.params["param_2"] == 20


def test_pending_order_pagination_uses_stable_tie_breaker():
    session = FakeSession()
    repository = OrderRepository(session)

    import asyncio
    result = asyncio.run(repository.list_by_delivery_status(DeliveryStatus.PENDING, limit=5, offset=10))

    compiled = session.statement.compile(dialect=postgresql.dialect())
    assert result == []
    assert "ORDER BY orders.created_at ASC, orders.id ASC" in str(compiled)
    assert compiled.params["param_1"] == 5
    assert compiled.params["param_2"] == 10
