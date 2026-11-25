from unittest.mock import Mock

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from scripts.configure_database import configure


def test_configuration_encodes_password_and_preserves_other_settings(tmp_path, capsys):
    path = tmp_path / ".env"
    path.write_text(
        "APP_ENV=development\nDATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/speech_to_text\nWHISPER_MODEL=base\n"
    )
    answers = iter(["", "", "", ""])
    assert configure(
        path, {}, prompt=lambda _: next(answers), password_prompt=lambda _: "p@ss:/#word"
    )
    values = dotenv_values(path)
    url = make_url(values["DATABASE_URL"])
    assert url.password == "p@ss:/#word"
    assert url.database == "speech_to_text"
    assert values["WHISPER_MODEL"] == "base"
    assert values["APP_ENV"] == "development"
    assert "p@ss:/#word" not in capsys.readouterr().out


def test_noninteractive_setup_does_not_prompt_or_write(tmp_path):
    path = tmp_path / ".env"
    path.write_text("DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost/db\n")
    original = path.read_text()
    prompt = Mock()
    with pytest.raises(ValueError, match="interactive"):
        configure(path, {}, prompt=prompt, interactive=False)
    prompt.assert_not_called()
    assert path.read_text() == original


def test_valid_existing_configuration_is_not_changed(tmp_path):
    path = tmp_path / ".env"
    original = "DATABASE_URL=postgresql+asyncpg://postgres:existing@localhost/speech_to_text\n"
    path.write_text(original)
    prompt = Mock()
    assert configure(path, {}, prompt=prompt) is False
    prompt.assert_not_called()
    assert path.read_text() == original


def test_empty_password_does_not_replace_config(tmp_path):
    path = tmp_path / ".env"
    path.write_text("DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost/db\n")
    original = path.read_text()
    with pytest.raises(ValueError, match="password"):
        configure(path, {}, prompt=lambda _: "", password_prompt=lambda _: "")
    assert path.read_text() == original


def test_environment_override_is_not_silently_written_to_file(tmp_path):
    path = tmp_path / ".env"
    path.write_text("APP_ENV=development\n")
    with pytest.raises(ValueError, match="environment variable"):
        configure(
            path, {"DATABASE_URL": "postgresql+asyncpg://postgres:your_password@localhost/db"}
        )
    assert path.read_text() == "APP_ENV=development\n"


def test_production_is_not_modified(tmp_path):
    path = tmp_path / ".env"
    path.write_text("APP_ENV=production\n")
    with pytest.raises(ValueError, match="development"):
        configure(path, {})
