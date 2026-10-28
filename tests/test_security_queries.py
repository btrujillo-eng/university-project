import asyncio
from typing import Any

from sqlalchemy.dialects import postgresql

from app.infrastructure.persistence.repositories.postgresql.product import ProductRepository


class FakeScalarResult:
    def all(self) -> list[Any]:
        return []


class FakeSession:
    def __init__(self) -> None:
        self.statement = None

    async def scalars(self, statement):
        self.statement = statement
        return FakeScalarResult()


def test_product_search_keeps_sql_injection_payload_as_bound_parameter() -> None:
    malicious_search = "' OR 1=1; DROP TABLE products; --"
    session = FakeSession()
    repository = ProductRepository(session)

    result = asyncio.run(repository.list_products(search_term=malicious_search))

    compiled = session.statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert result == []
    assert "DROP TABLE products" not in sql
    assert any(malicious_search in str(value) for value in compiled.params.values())
    assert "ILIKE" in sql
