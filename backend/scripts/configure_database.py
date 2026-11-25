"""Prompt locally for missing database credentials without displaying the password."""

import argparse
import getpass
import os
import sys
import warnings
from pathlib import Path

from dotenv import dotenv_values, set_key
from sqlalchemy.engine import URL, make_url

DEFAULT_URL = "postgresql+asyncpg://postgres:your_password@localhost:5432/speech_to_text"


def configure(
    path, environ, prompt=input, password_prompt=getpass.getpass, *, force=False, interactive=True
):
    values = dotenv_values(path, interpolate=False)
    if environ.get("APP_ENV", values.get("APP_ENV") or "development") != "development":
        raise ValueError(
            "Interactive database setup is development-only; production settings were not changed."
        )
    raw = environ.get("DATABASE_URL") or values.get("DATABASE_URL") or DEFAULT_URL
    try:
        existing = make_url(raw)
    except Exception:
        raise ValueError(
            "DATABASE_URL is malformed. Correct it in backend/.env before continuing."
        ) from None
    # Detect the public template placeholder; it is never used to authenticate here.
    missing = raw == DEFAULT_URL or existing.password == "your_password"  # nosec B105
    if not force and not missing:
        return False
    if "DATABASE_URL" in environ:
        raise ValueError(
            "DATABASE_URL is set as an environment variable. Correct or unset it in this "
            "terminal first; it overrides backend/.env."
        )
    if not interactive:
        raise ValueError(
            "Database credentials are missing. Run python run.py in an interactive "
            "terminal to enter them, or edit backend/.env."
        )
    print(
        "PostgreSQL connection setup. Press Enter to accept each default.\n"
        "Enter your existing PostgreSQL password; this does not change or reset it.",
        flush=True,
    )

    def field(label, default):
        value = prompt(f"{label} [{default}]: ").strip() or default
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError(f"{label} cannot be empty or contain control characters.")
        return value

    host = field("Host", existing.host or "localhost")
    port_text = field("Port", str(existing.port or 5432))
    if not port_text.isdecimal() or not 1 <= int(port_text) <= 65535:
        raise ValueError("Port must be a number between 1 and 65535.")
    username = field("Username", existing.username or "postgres")
    database = field("Database", existing.database or "speech_to_text")
    # Fail rather than fall back to visible password input on unsupported terminals.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = password_prompt("PostgreSQL password (hidden): ")
    if not password:
        raise ValueError("A PostgreSQL password is required; no settings were changed.")
    url = URL.create(
        "postgresql+asyncpg",
        username=username,
        password=password,
        host=host,
        port=int(port_text),
        database=database,
        query=existing.query,
    )
    set_key(path, "DATABASE_URL", url.render_as_string(hide_password=False), quote_mode="always")
    print(
        "Database connection saved to the ignored backend/.env file. Password was not displayed.",
        flush=True,
    )
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Re-enter existing connection settings"
    )
    args = parser.parse_args()
    try:
        configure(
            Path(__file__).resolve().parents[1] / ".env",
            os.environ,
            force=args.force,
            interactive=sys.stdin.isatty(),
        )
        return 0
    except (ValueError, OSError, EOFError, getpass.GetPassWarning) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDatabase setup cancelled. Settings were not changed.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
