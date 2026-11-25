# Cloud deployment progress

Deployment requested on 2026-11-25. Source revision: `1887b2c14ed86f71c05596b28d8f41d1ffb4b535` (`main`), verified against GitHub. Deployment is **not yet complete**.

## Provisioned resources

- Neon project `dark-bar-35215523`, Singapore, database `speech_to_text`, branch `br-divine-water-bi0op8zp` (`production`). Dedicated `app.db.init_db` initialization succeeded using TLS and the administrator connection. Tables: `users`, `tickets`, `transcriptions`. Runtime role `stt_app` has read/write access; administrator credentials are not deployed to services.
- Railway project `a6053616-1f88-4767-9756-11d5d5a35ba6`, production environment `74003e0b-c138-40b4-b885-e98b6c419291`, service `04ef60b2-f97e-451c-b352-416328317035` (`whisper-worker`). Live at `https://whisper-worker-production-52ccf09e.up.railway.app`. Deployment `d33728f8-5470-43f5-817d-0897df52e9b9` reports SUCCESS. Source is pinned to the revision above.
- Railway configured with `/backend` root, Railpack, Python 3.12, CPU-only PyTorch installation, original Whisper, FFmpeg, port 8001, single inference session, `/health` health check, and production database/service secrets. Exact allowed origin: `https://speech-to-text-web-codecrafter1859.vercel.app`. Explicitly create `/app/.venv` during custom installation and start `/app/.venv/bin/python`; the system interpreter does not contain the installed dependencies. Verified commands are documented in `backend/README.md`.
- Vercel team access is now approved. Frontend project `prj_WnaT7al1lR3AQ3nDlStoKvJ00H0q`, deployment `dpl_AwtrwrTUmvWwfcLNzjWZca9zscXo`, is READY and serves HTTPS 200 at `https://speech-to-text-web-codecrafter1859.vercel.app`. It includes a local CSP change restricting connections to the two production service hosts. Source uploaded directly through the authenticated Vercel API because the team's GitHub integration was unavailable; no automatic Git deployment is configured.
- REST project `prj_GhywMhLaCG9RA8OfCexfzS7jhvUj` (`speech-to-text-api`) was created and deployed. Initial runtime failed because Vercel prioritized `pyproject.toml`, which lacked runtime dependencies. Added `[project]` metadata with pins matching `requirements.txt`; replacement deployment `dpl_7dDi4qmGKz4vgS66MSYJvLW6gwod` received production aliases. Before health verification, the project was deleted outside this agent session at 2026-11-25 18:19:18 UTC, confirmed by Vercel event `uev_ueziGCQjTIeNtUHEwHXNUOj5`. User clarification is pending before recreating it. The frontend's API URL currently points at this missing project.
- Production user provisioned in Neon. Access token saved only in ignored `backend/.cache/deployment/production-login.txt` and JSON alongside it. Do not print or commit it.

## Verification this attempt

All commands executed from the corresponding backend/frontend directory. Successful commands returned exit code 0:

- Backend: `.venv/Scripts/python.exe -m pytest -q`: 50 passed, one Starlette TestClient deprecation warning.
- Backend: `.venv/Scripts/python.exe -m ruff check app transcription_worker scripts tests`: passed.
- Backend: `.venv/Scripts/python.exe -m bandit -r app transcription_worker scripts -q`: passed.
- Frontend: `npm.cmd test -- --run`: 9 passed.
- Frontend: `npm.cmd run lint`: passed.
- Frontend: `npm.cmd run build`: TypeScript and Vite production build passed.
- Frontend: `npm.cmd audit --omit=dev --audit-level=high`: zero vulnerabilities.
- Worker: `.venv/Scripts/python.exe -m pip_audit --path .venv-worker/Lib/site-packages --progress-spinner off --format json --output .cache/deployment/worker-audit.json`: initially failed on pip 24.2 advisories; upgraded worker pip to 26.3 and reran successfully, zero known vulnerabilities. This checks the local Windows environment; the deployed Linux dependency resolution still needs verification.

Initial sandbox network attempts for GitHub, audits, and database initialization failed; approved network retries succeeded. No failed check is counted as a pass without its successful retry.

## Live verification

- Frontend HTTPS page: 200. No browser-driven visual or microphone check completed.
- Worker HTTPS health: 200, original multilingual base model loaded.
- Synthetic English WAV upload: 201, exact test sentence recognized, transcript persisted to Neon, exact CORS origin returned.
- Reusing the upload ticket: 401 as expected.
- First WebSocket test sent audio faster than real time with Python-client keepalive enabled and failed with a ping timeout. Follow-up used microphone-paced PCM and browser-equivalent behavior (no client-generated ping frames), retained a 180-second receive deadline, and passed: ready, pause/resume, partial results, final result and persistence. Streaming text had a repeated phrase at an overlap boundary; recognition and deduplication remain imperfect.
- Smoke script `.cache/deployment/worker_smoke.py` removed only the successful synthetic test records it created. A failed/interrupted first stream may remain in history as a failed session. No user recordings were removed.
- Local Ruff and TOML dependency-pin consistency check passed after packaging changes. No runtime application code changed.

## Remaining deployment steps

1. Obtain clarification about the externally deleted API project. If recreation is approved, recreate `speech-to-text-api` with root `backend`, restore its production env from ignored `runtime.json`, and restore `speech-to-text-api-codecrafter1859.vercel.app`.
2. Deploy the corrected `pyproject.toml` with REST source only. Verify `/ready`, login, unauthenticated denial, owner isolation, CRUD and API-issued worker tickets.
3. Complete browser and Hindi/mixed microphone acceptance checks. Verify the deployed Linux dependency resolution, resource use, monitoring, and edge rate limits. Local Windows dependency audit does not cover Linux-only packages.
4. Commit reviewed deployment fixes and documentation when final; unrelated untracked `skill.md` remains untouched. Connect Vercel's GitHub integration separately if automatic deployments are desired.

Secrets are stored only in provider settings and ignored `backend/.cache/deployment/` files. Do not commit, upload as artifacts, or print those files. Existing local `.env` files were preserved.
