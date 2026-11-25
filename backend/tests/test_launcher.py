import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import run as launcher


def test_real_children_are_stopped_after_service_exit(monkeypatch):
    children = []

    def spawn(service, env):
        child = launcher.spawn_service(service, env)
        children.append(child)
        return child

    monkeypatch.setattr(launcher, "healthy", lambda url: False)
    services = [
        launcher.Service(
            "short", [sys.executable, "-c", "import time; time.sleep(0.2)"], Path("."), ""
        ),
        launcher.Service(
            "long", [sys.executable, "-c", "import time; time.sleep(60)"], Path("."), ""
        ),
    ]
    import os

    assert launcher.supervise(services, os.environ.copy(), spawn=spawn) == 1
    assert all(child.poll() is not None for child in children)


def test_missing_prerequisites_do_not_start_children(monkeypatch):
    monkeypatch.setattr(launcher, "prerequisites", lambda: ["ffmpeg is missing"])
    start = Mock()
    monkeypatch.setattr(launcher, "supervise", start)
    assert launcher.main([]) == 1
    start.assert_not_called()


def test_preparation_rejects_production(monkeypatch):
    from types import SimpleNamespace

    from scripts import prepare_local

    monkeypatch.setattr(
        prepare_local, "get_settings", lambda: SimpleNamespace(app_env="production")
    )
    with pytest.raises(RuntimeError, match="development-only"):
        prepare_local.validate_config()


async def test_first_run_creates_one_user_and_never_rotates_existing_token(
    database, monkeypatch, capsys
):
    from sqlalchemy import delete, select

    from app.db import database as db_module
    from app.models.transcription import User
    from scripts.prepare_local import prepare

    monkeypatch.setattr(db_module, "Session", database)
    monkeypatch.setattr(db_module, "engine", database.kw["bind"])
    async with database() as db:
        await db.execute(delete(User))
        await db.commit()
    await prepare()
    assert "First-run login token" in capsys.readouterr().out
    async with database() as db:
        first = (await db.scalars(select(User))).one()
        original_hash = first.token_hash
    await prepare()
    assert "First-run login token" not in capsys.readouterr().out
    async with database() as db:
        assert (await db.scalars(select(User))).one().token_hash == original_hash


def test_plan_runs_servers_directly_without_reload(tmp_path):
    plan = launcher.service_plan(tmp_path, Path(sys.executable), Path(sys.executable), "node")
    assert [item.name for item in plan] == ["REST API", "Whisper worker", "Frontend"]
    assert "--reload" not in plan[0].command
    assert plan[2].command[1].endswith("vite.js")
    assert "--strictPort" in plan[2].command


def test_supervisor_cleans_started_children_on_launch_failure():
    process = Mock()
    process.poll.return_value = None
    stop = Mock()
    services = [
        launcher.Service("first", ["python"], Path("."), "http://localhost:1"),
        launcher.Service("second", ["python"], Path("."), "http://localhost:2"),
    ]
    spawn = Mock(side_effect=[process, OSError("launch failed")])
    with pytest.raises(OSError):
        launcher.supervise(services, {}, spawn=spawn, stop=stop)
    stop.assert_called_once_with(process)


def test_supervisor_stops_every_service_when_one_exits():
    failed, running = Mock(), Mock()
    failed.poll.return_value = 2
    running.poll.return_value = None
    stop = Mock()
    services = [
        launcher.Service("first", [], Path("."), ""),
        launcher.Service("second", [], Path("."), ""),
    ]
    result = launcher.supervise(services, {}, spawn=Mock(side_effect=[failed, running]), stop=stop)
    assert result == 1
    assert stop.call_count == 2


def test_help_never_installs_or_starts_services():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "run.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--check" in result.stdout
