# Cloud deployment progress

Deployment requested on 2026-11-25. Source revision: `1887b2c14ed86f71c05596b28d8f41d1ffb4b535` (`main`), verified against GitHub. Deployment is **not yet complete**.

## Provisioned resources

- Neon project `dark-bar-35215523`, Singapore, database `speech_to_text`, branch `br-divine-water-bi0op8zp` (`production`). Dedicated `app.db.init_db` initialization succeeded using TLS and the administrator connection. Tables: `users`, `tickets`, `transcriptions`. Runtime role `stt_app` has read/write access; administrator credentials are not deployed to services.
- Railway project `a6053616-1f88-4767-9756-11d5d5a35ba6`, production environment `74003e0b-c138-40b4-b885-e98b6c419291`, service `04ef60b2-f97e-451c-b352-416328317035` (`whisper-worker`). Domain reserved: `whisper-worker-production-52ccf09e.up.railway.app`. Git source is staged at the revision above; it has **not been built or started**.
- Railway configured with `/backend` root, Railpack, Python 3.12, CPU-only PyTorch installation, original Whisper, FFmpeg, port 8001, single inference session, `/health` health check, and production database/service secrets. `CORS_ORIGINS` still requires the actual Vercel frontend origin before deployment.
- Vercel team `team_j61ZHCkJk65R8SrTAWLjBk2H` (`ashutosh-sirs-projects`) returns HTTP 403 until the user grants team access through the generated consent link. No Vercel projects or deployments created yet.

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

## Remaining deployment steps

1. Retry Vercel project listing after team-access consent. Create frontend/backend projects with their respective root directories, linked to the verified GitHub source.
2. Configure exact production origins, HTTPS/WSS URLs and secret environment variables; tighten frontend CSP to actual hosts.
3. Review staged Railway changes, deploy the worker, inspect build/runtime logs and verify model/FFmpeg readiness. Verify the Linux dependency resolution and resource use.
4. Provision the production application user, saving the token privately. Deploy and verify REST `/ready`, unauthenticated denial, owner isolation, CRUD and worker ticket/WebSocket flow. Build/deploy the frontend with actual production URLs.
5. Complete real audio/browser smoke tests; report any device-dependent acceptance checks still requiring the user.

Secrets are stored only in provider settings and ignored `backend/.cache/deployment/` files. Do not commit, upload as artifacts, or print those files. Existing local `.env` files were preserved.
