from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.engine import make_url

from scripts.create_database import ensure_database


class DatabaseError(Exception):
    def __init__(self, code):
        self.sqlstate = code


def connection(error=None):
    context = AsyncMock()
    if error:
        context.__aenter__.side_effect = error
    return context


def target(name="speech_to_text", error=None):
    return SimpleNamespace(
        url=make_url("postgresql+asyncpg://user:secret@localhost/postgres").set(database=name),
        dialect=dialect(),
        connect=Mock(side_effect=[connection(error), connection()]),
    )


async def test_existing_database_does_not_require_create_privilege(monkeypatch):
    factory = Mock()
    monkeypatch.setattr("scripts.create_database.create_async_engine", factory)
    assert await ensure_database(target()) is False
    factory.assert_not_called()


async def test_missing_database_uses_autocommit_quotes_name_and_preserves_ssl(monkeypatch):
    engine = target('words"; DROP DATABASE postgres; --', DatabaseError("3D000"))
    context = connection()
    maintenance = SimpleNamespace(connect=Mock(return_value=context), dispose=AsyncMock())
    factory = Mock(return_value=maintenance)
    monkeypatch.setattr("scripts.create_database.create_async_engine", factory)
    assert await ensure_database(engine, {"ssl": "verified-context"}) is True
    assert factory.call_args.args[0].database == "postgres"
    assert factory.call_args.kwargs["isolation_level"] == "AUTOCOMMIT"
    assert factory.call_args.kwargs["connect_args"] == {"ssl": "verified-context"}
    sql = str(context.__aenter__.return_value.execute.call_args.args[0])
    assert sql == 'CREATE DATABASE "words""; DROP DATABASE postgres; --"'
    maintenance.dispose.assert_awaited_once()
    assert engine.connect.call_count == 2


@pytest.mark.parametrize("code", ["28P01", "08001", "42501"])
async def test_other_connection_failures_never_create_database(monkeypatch, code):
    factory = Mock()
    monkeypatch.setattr("scripts.create_database.create_async_engine", factory)
    with pytest.raises(DatabaseError):
        await ensure_database(target(error=DatabaseError(code)))
    factory.assert_not_called()


@pytest.mark.parametrize("code", ["42P04", "23505"])
async def test_concurrent_creation_rechecks_target(monkeypatch, code):
    context = connection()
    context.__aenter__.return_value.execute.side_effect = DatabaseError(code)
    maintenance = SimpleNamespace(connect=Mock(return_value=context), dispose=AsyncMock())
    monkeypatch.setattr(
        "scripts.create_database.create_async_engine", Mock(return_value=maintenance)
    )
    engine = target(error=DatabaseError("3D000"))
    assert await ensure_database(engine) is False
    assert engine.connect.call_count == 2
    maintenance.dispose.assert_awaited_once()


async def test_creation_permission_error_is_actionable(monkeypatch):
    context = connection()
    context.__aenter__.return_value.execute.side_effect = DatabaseError("42501")
    maintenance = SimpleNamespace(connect=Mock(return_value=context), dispose=AsyncMock())
    monkeypatch.setattr(
        "scripts.create_database.create_async_engine", Mock(return_value=maintenance)
    )
    with pytest.raises(RuntimeError, match="CREATEDB"):
        await ensure_database(target(error=DatabaseError("3D000")))
    maintenance.dispose.assert_awaited_once()


async def test_overlong_database_name_rejected():
    with pytest.raises(RuntimeError, match="63"):
        await ensure_database(target("x" * 64))
