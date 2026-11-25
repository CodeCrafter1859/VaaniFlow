# Local launcher verification — 2026-11-25

Reviewed revision: base `6c95f6d` plus the local-launcher working-tree changes (`backend/run.py`, `backend/scripts/prepare_local.py`, `backend/tests/test_launcher.py`, `.vercelignore`, and documentation).

Commands ran from `backend` using `.venv/Scripts/python.exe`:

| Command | Exit | Observed result |
|---|---:|---|
| `-m pytest tests/test_launcher.py -q` before implementation | 1 | Expected collection failure: launcher module did not exist |
| `-m pytest tests/test_launcher.py -q` initial implementation | 0 | 4 tests passed |
| `-m pytest -q` final expanded suite | 0 | **35 passed**, one existing Starlette HTTPX deprecation warning |
| `-m ruff check app transcription_worker scripts tests run.py` | 0 | All checks passed |
| `-m ruff format --check run.py scripts/prepare_local.py tests/test_launcher.py` | 0 | Three files already formatted |
| `-m bandit -r app transcription_worker scripts run.py -q` | 0 | No findings; narrowly annotated fixed-argv process calls and hardcoded loopback HTTP health probes reviewed |
| `-m compileall -q run.py scripts/prepare_local.py` | 0 | New Python entrypoints compiled |
| `run.py --help` | 0 | Documented CLI rendered without starting/installing services |
| `run.py --check` | 1 | Correctly reported FFmpeg missing, port 8000 occupied and worker dependencies missing |
| `-m scripts.prepare_local --check-config` | 1 | Correctly rejected the placeholder PostgreSQL password in the current `.env` |
| `git diff --check` | 0 | No whitespace errors |

Eight launcher tests cover command planning without reloader/npm wrapper processes, non-mutating help, preflight failure, launch-failure cleanup, sibling exit shutdown, **real** child-process cleanup, production rejection and idempotent first-user creation. Existing users and token digests remain unchanged on repeat setup.

Full service/model startup was **not verified** because FFmpeg is unavailable and port 8000 is occupied by an existing service. The launcher does not stop that unrelated process. Project dependencies bootstrap on normal startup once system prerequisites are satisfied; model inference remains covered by mocks in automated tests. PostgreSQL operating-system service startup and database creation require one-time setup and are not silently attempted with administrator privileges.

No frontend application or dependency changes were made; rerunning the unchanged frontend build or advisory audits was not applicable to this launcher-only change. Prior results remain in RESULTS.md. Packaging verification here consists of Python compilation and confirming `run.py` is excluded from Vercel; production application entrypoints are unchanged. No deployment was performed.

## Follow-up: automatic database creation

The later user request authorizes creation of the configured database when missing. This supersedes the original database-creation prerequisite above. PostgreSQL itself must still be running, credentials must be valid, and the configured role needs CREATEDB plus maintenance-database CONNECT permissions for initial creation. No privileges are changed automatically.

Reviewed against `6c95f6d` plus the launcher working tree and new `scripts/create_database.py` / `tests/test_create_database.py`. The helper probes the target first and creates only on SQLSTATE 3D000. It preserves TLS/connection settings, quotes identifiers using the dialect, creates outside a transaction, handles concurrent creation by rechecking the target, and always disposes the maintenance engine.

Observed commands from backend, using `.venv/Scripts/python.exe`:

- `-m pytest tests/test_create_database.py -q`: first run exited 1 because the helper was not implemented; after implementation exited 0, **9 passed**.
- `-m pytest -q`: exited 0, **44 passed**, one unchanged upstream HTTPX deprecation warning.
- `-m ruff check app transcription_worker scripts tests run.py`: exited 0, all checks passed.
- `-m ruff format --check scripts/create_database.py scripts/prepare_local.py tests/test_create_database.py`: exited 0, three files formatted.
- `-m bandit -r scripts/create_database.py scripts/prepare_local.py -q`: exited 0, no findings.
- `-m compileall -q scripts/create_database.py scripts/prepare_local.py`: exited 0.
- One-off Python stdin smoke against isolated PostgreSQL 18 on port 55439: exited 0. Created a randomly named database containing a quote, inserted a marker row, called the helper again, and verified the marker remained. A temporary role without CREATEDB received the expected actionable error. The script dropped only its own temporary database/role afterward, and the test server was stopped.
- `git diff --check`: exited 0.

No dependency, frontend runtime or production entrypoint changes; prior advisory audits/frontend build results remain applicable. The user's configured database was not modified during testing; normal `python run.py` now creates it when required.

## Follow-up: interactive database credentials

Added `scripts/configure_database.py` before the launcher's configuration check. When the default password is present, interactive startup prompts for connection settings and a hidden existing PostgreSQL password, safely URL-encodes it, and updates only DATABASE_URL in the ignored `.env`. Existing valid configurations are preserved. Production, noninteractive prompting and conflicting process environment overrides are rejected. Setup subprocess errors now retain their actionable message without the distracting Python command/exit-status wrapper.

Reviewed on base `6c95f6d` plus the local startup working tree. Targeted tests initially failed with missing module (exit 1), then passed after implementation. Final `python -m pytest -q` from backend: exit 0, **50 passed**, one unchanged upstream deprecation warning. `ruff check`, `ruff format --check` for the three changed Python files, `compileall` for the launcher/configuration script and `git diff --check` all exited 0. Bandit initially flagged detection of the public `your_password` template as a hardcoded credential; that comparison is narrowly annotated and documented, and the final targeted Bandit scan exited 0.

Tests verify special-character password round-trip, no password in stdout, preservation of unrelated settings, no mutation on empty password, existing configuration preservation, production/environment-override rejection and noninteractive refusal. Password prompts are injected in tests; no actual database password was requested or written during verification. A real terminal run and authentication still require the user's existing PostgreSQL credentials. No dependency/frontend changes, so unchanged advisory audits and frontend build were not repeated.
