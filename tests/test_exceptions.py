import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from app.api.exception_handlers import AppExceptionHandlers


def _build_test_app() -> FastAPI:
    """Мини-приложение с теми же обработчиками ошибок, что и в основном app.main."""
    test_app = FastAPI()
    AppExceptionHandlers().register(test_app)

    class _FakeOrig:
        def __init__(self, pgcode: str):
            self.pgcode = pgcode

    @test_app.get("/raise-value-error")
    async def raise_value_error():
        raise ValueError("bad input")

    @test_app.get("/raise-integrity-unique")
    async def raise_integrity_unique():
        raise IntegrityError("stmt", {}, _FakeOrig("23505"))

    @test_app.get("/raise-integrity-fk")
    async def raise_integrity_fk():
        raise IntegrityError("stmt", {}, _FakeOrig("23503"))

    @test_app.get("/raise-integrity-notnull")
    async def raise_integrity_notnull():
        raise IntegrityError("stmt", {}, _FakeOrig("23502"))

    @test_app.get("/raise-operational-error")
    async def raise_operational_error():
        raise OperationalError("stmt", {}, Exception("connection lost"))

    @test_app.get("/raise-sqlalchemy-error")
    async def raise_sqlalchemy_error():
        raise SQLAlchemyError("generic db error")

    return test_app


@pytest.fixture
async def exc_client():
    """HTTP клиент для мини-приложения с обработчиками ошибок."""
    test_app = _build_test_app()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestExceptionHandlers:
    """Тесты глобальных обработчиков ошибок из app/core/exception_handlers.py."""

    async def test_value_error_returns_400(self, exc_client: AsyncClient):
        response = await exc_client.get("/raise-value-error")
        assert response.status_code == 400
        assert response.json()["detail"] == "bad input"

    async def test_integrity_unique_violation_returns_409(self, exc_client: AsyncClient):
        response = await exc_client.get("/raise-integrity-unique")
        assert response.status_code == 409

    async def test_integrity_fk_violation_returns_409(self, exc_client: AsyncClient):
        response = await exc_client.get("/raise-integrity-fk")
        assert response.status_code == 409

    async def test_integrity_notnull_violation_returns_400(self, exc_client: AsyncClient):
        response = await exc_client.get("/raise-integrity-notnull")
        assert response.status_code == 400

    async def test_operational_error_returns_503(self, exc_client: AsyncClient):
        response = await exc_client.get("/raise-operational-error")
        assert response.status_code == 503

    async def test_generic_sqlalchemy_error_returns_500(self, exc_client: AsyncClient):
        response = await exc_client.get("/raise-sqlalchemy-error")
        assert response.status_code == 500
