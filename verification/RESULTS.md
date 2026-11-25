# Verification results — 2026-11-25

Implementation reviewed against base revision `a34930640a71c06b9533bad3c245db48e786cd08` plus the application changes in this delivery. Tests were executed on Windows with Python 3.12.7, Node 22.19.0, PostgreSQL 18, pytest 9.2.0, Vitest 5.1.2, TypeScript 7.0.2, Vite 8.3.8, Ruff 0.17.6, Bandit 1.9.4 and pip-audit 2.10.1. Source fingerprints are recorded in `source-sha256.json`.

## Observed results

Commands below ran from the specified independent project directory. On Windows `python` was `backend/.venv/Scripts/python.exe` and npm was invoked as `npm.cmd`.

| Directory | Command/check | Exit | Result |
|---|---|---:|---|
| backend | `python -m pytest -q` | 0 | **27 passed** on temporary SQLite databases |
| backend | `$env:TEST_DATABASE_URL='postgresql+asyncpg://stt_test@127.0.0.1:55439/postgres'; python -m pytest -q` | 0 | **27 passed** on isolated PostgreSQL schemas |
| backend | `python -m ruff check app transcription_worker scripts tests` | 0 | All checks passed |
| backend | `python -m ruff format --check app transcription_worker scripts tests` | 0 | 39 files already formatted |
| backend | `python -m bandit -r app transcription_worker scripts -q` | 0 | No remaining findings after explicit reviews noted below |
| backend | `python -m compileall -q app transcription_worker scripts` | 0 | Source compiled |
| backend | `python -m pip_audit --progress-spinner off --format json --output verification-audit.json` | 0 | No known vulnerabilities; saved as `verification/backend-audit.json` |
| backend | `python -m app.db.init_db` with isolated local PostgreSQL URL | 0 | `create_all` initialization succeeded |
| backend | HTTPX ASGI smoke against `/health`, `/ready`, `/openapi.json`, `/docs` | 0 | All four returned 200; PostgreSQL readiness passed; asserted neither `whisper` nor `torch` was imported by REST |
| frontend | `npm run lint` | 0 | No warnings in final run |
| frontend | `npm test` | 0 | **9 passed**, three test files |
| frontend | `npm run build` | 0 | TypeScript project checks and Vite production build passed |
| frontend | `npm audit --audit-level=moderate` | 0 | 0 vulnerabilities in the npm lockfile |
| root | `git diff --check` | 0 | No whitespace errors |
| root | `git check-ignore backend/.env frontend/.env backend/.venv backend/.test-postgres` | 0 | Actual environments, virtualenv and test DB ignored |
| root | Targeted private-key/AWS/GitHub/OpenAI secret-signature scan of Git-visible files | 0 | 102 files scanned at time of check, zero findings; this is not a comprehensive secret scanner |

Final frontend bundle: JS 298.59 kB (94.72 kB gzip), CSS 23.84 kB (6.63 kB gzip). This measures bundle size, not browser rendering speed or inference throughput.

## Tests and review

Backend coverage includes CRUD and cross-owner denial; validation/null rejection; literal search/filter/sort/pagination; dashboard aggregates; one-use tickets, expiry, wrong-purpose denial and concurrent consumption; CORS/security headers; invalid MIME/signatures/body limits; Unicode overlap deduplication; session cleanup; interrupted-session persistence; authenticated direct upload/replay rejection; and actual ASGI WebSocket routing with mocked inference. Frontend tests exercise Fetch response/error/auth/FormData behavior, login errors, real API-shaped dashboard/history interactions, edit/delete confirmation, microphone denial and recording lifecycle ordering/cleanup.

Observed red→green fixes:

- Hindi deduplication regression: `python -m pytest tests/test_text.py -q` initially had **1 failed, 3 passed**, collapsing distinct vowel marks in `की` and `कि`. Unicode category-based punctuation removal replaced `\w` filtering; rerun **4 passed** and full regressions passed.
- The added PostgreSQL/ASGI socket integration test initially failed (**1 failed, 26 passed**) because the test fixture reused a pooled connection across event loops. Using `NullPool`, matching the application engine, produced **27 passed**.
- The first frontend build caught a malformed JSX option tag. The corrected markup passed TypeScript and production builds.
- Review found a rapid pause/resume ordering race. Both controls now reach the socket in AudioWorklet acknowledgement order; a lifecycle assertion covers deferred resume transmission.

Bandit triage: `0.0.0.0` is an intentional configurable service bind; deployment instructions require a TLS/firewall boundary. FFmpeg is an intentional subprocess with fixed argv, no shell, temporary input, protocol allowlist, duration/size limits and timeout. Only these reviewed source lines have narrowly scoped `nosec` annotations. No blanket scanner rule suppression was added.

The initial Python environment audit reported advisories in pip 24.2 (no application-package findings). The isolated venv's pip was upgraded to 26.3; the final audit passed. Original Whisper/PyTorch are deliberately absent from the REST/dev environment and are **not covered by that audit**.

One non-failing upstream deprecation warning remains: Starlette TestClient announces future migration from HTTPX to HTTPX2. The requested native Fetch/HTTPX integration still works with the pinned tested versions. No tests are skipped or disabled.

Architecture/security review: REST imports no model runtime, owner scope is enforced before CRUD, SQLAlchemy parameterizes queries, random tokens are hashed in storage, worker tickets are short-lived and atomically consumed, audio/model output is treated as text, raw uploads are bounded before parsing, inference runs outside the event loop with bounded admission, and temp audio is cleaned up. The design avoids holding full session audio in memory. Large-history substring search and model latency require workload-specific measurement; there is no claimed throughput benchmark.

## Remaining release gates — not verified

- **Actual Whisper/PyTorch environment installation, resolved dependency audit and model inference accuracy** on the target CPU/GPU. Automated inference was mocked as requested; FFmpeg was not available on this shell's PATH. The real microphone script is supplied but not run.
- **Browser visual/device QA:** no browser automation/preview tool was available in this session. React interaction tests and builds do not establish microphone hardware, cross-browser AudioWorklet behavior, responsive appearance or keyboard behavior in a real browser.
- **Hosted deployment:** no Vercel, Neon or Railway/server credentials or deployment targets were supplied. TLS/WSS, exact CORS origins, provider request/time limits, proxy rate/IP connection limits, model cache and production load need staging verification. Current official provider documentation was consulted; this is prepared configuration, not a deployed-and-verified service.
- Worker dependency locking/audit, edge rate limiting and model throughput testing are required before a public production-ready claim. Session limits are per process, not a distributed quota. No durable queued jobs or cross-worker stream recovery are provided.

The local PostgreSQL test cluster was created solely for this task and stopped after verification. Actual `.env` files remain local and ignored. No model weights, audio recordings, user tokens or database files are intended for version control.
