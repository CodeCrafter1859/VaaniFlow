# Speech to Text API and Whisper worker

Two independently hosted Python services share PostgreSQL. `app.main:app` is the lightweight FastAPI REST service. `transcription_worker.main:app` owns WebSockets, FFmpeg and original open-source OpenAI Whisper inference. No paid transcription service, Alembic or Docker is used.

## Local installation

Use Python 3.12 and PostgreSQL 15+. From `backend/`:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
# If activation is restricted, use .venv\Scripts\python.exe instead of python.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

REST requirements intentionally exclude Whisper, NumPy and PyTorch. Install the worker in a **separate environment** on the worker machine (or `.venv-worker` locally):

```bash
python -m venv .venv-worker
source .venv-worker/bin/activate
python -m pip install --upgrade pip
python -m pip install -r transcription_worker/requirements.txt
```

Run all commands from `backend`, including worker commands. Install FFmpeg and make `ffmpeg -version` work in the worker shell:

- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: `choco install ffmpeg` if Chocolatey is installed, or install a Windows build linked from [FFmpeg downloads](https://ffmpeg.org/download.html) and add its `bin` directory to PATH.

The worker loads `WHISPER_MODEL=base` on startup, downloading weights on first use. Allow outbound access for the first download and persist the model cache (`~/.cache/whisper`). Start with CPU; a compatible CUDA PyTorch installation is needed for `WHISPER_DEVICE=cuda`. See [original Whisper installation/model guidance](https://github.com/openai/whisper). Never use an English-only `.en` model for Hindi.

## Environment and database

Copy `.env.example` to `.env` if not already present. Actual `.env` is ignored. Set the PostgreSQL password, database name and a random service key (generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`). The REST service and worker must use the same database and `TRANSCRIPTION_SERVICE_API_KEY`. Keep this key out of frontend variables and logs.

Create an empty development database using your PostgreSQL administrator account:

```bash
createdb -U postgres speech_to_text
python -m app.db.init_db
python -m scripts.create_user "Your name"
```

`create_all()` runs **only** in the dedicated initialization script, not on requests or serverless cold starts. It creates users, one-use tickets and transcriptions. It does not alter existing tables; future schema changes require reviewed SQL and backups. The transcription includes the requested fields plus an indexed `owner_id` for authorization. `create_user` prints a cryptographically random access token once; only a SHA-256 digest is stored. Transfer the token privately and enter it at the frontend sign-in screen. There is no public registration or shared default account. To revoke/rotate a token, replace that user's `token_hash` through an administrator script or approved database operation; tickets already issued expire within 60 seconds and active streams finish within the session limit.

```bash
# REST environment, terminal 1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# Worker environment, terminal 2
python -m uvicorn transcription_worker.main:app --host 127.0.0.1 --port 8001 --ws-max-size 32768 --ws-max-queue 8 --limit-concurrency 32
```

Swagger: `http://localhost:8000/docs`. Liveness: `/health`. Database readiness: `/ready`. Worker `/health` becomes available after model loading. Frontend instructions are in [../frontend/README.md](../frontend/README.md).

## REST contract

All private routes require `Authorization: Bearer <user-token>`. Every query/mutation is owner-scoped; inaccessible IDs return 404. Success is `{ "data": ... }`; failures are `{ "error": { "code": "...", "message": "..." } }`. Swagger includes typed CRUD request/response models.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness; no auth |
| GET | `/ready` | Database connectivity; no auth |
| GET | `/api/v1/auth/me` | Token verification and current profile |
| POST | `/api/v1/auth/ticket?purpose=websocket` | 60-second one-use worker ticket (`upload` also supported) |
| POST | `/api/v1/transcriptions` | Save a text transcript; 201 |
| GET | `/api/v1/transcriptions` | Search/filter/sort/page |
| GET/PATCH/DELETE | `/api/v1/transcriptions/{id}` | Read, edit title/text, permanently delete |
| POST | `/api/v1/transcriptions/audio` | Multipart `file` and optional `title`; proxy to worker; 201 |
| GET | `/api/v1/dashboard/stats` | Owner's total/completed/failed counts, seconds, language counts |

Create example: `{"title":"Meeting","text":"नमस्ते hello","language":"hi","duration":12.5,"status":"completed"}`. Durations are seconds, IDs are UUIDs, timestamps are UTC. PATCH accepts a non-null `title` and/or `text`. Statuses are `completed` and `failed`; active recording state is kept in the worker until completion/disconnect.

List parameters: `search` (literal title/text substring, up to 200 chars), `language` (Whisper code), `status`, `sort=created_at|title|duration`, `order=asc|desc`, `page>=1`, `page_size=1..100`. Response: `{data:{items:[],total:0,page:1,page_size:10}}`. UUID provides a stable sorting tiebreaker. Contains searches are deliberately simple; add measured PostgreSQL trigram indexes if history grows large.

### Uploads

WAV, MP3, M4A, WebM, OGG and FLAC; maximum 10 MiB and 300 decoded seconds by default. MIME allowlist, signature check, FFmpeg decode validation, raw body limit and decode timeout are enforced. Audio temp files are deleted in `finally`; raw audio is not stored. FFmpeg executes a fixed argument list without a shell, with file/pipe protocols only, and decodes at most `MAX_SESSION_DURATION+1` seconds.

For the browser and production, first request an upload ticket from REST, then POST multipart directly to the returned `upload_url` with `X-Upload-Ticket: <ticket>`. This avoids Vercel request-size and inference-duration limits. A ticket is consumed even if the upload fails; obtain a new one to retry. Worker `/internal/audio` is only for the REST proxy and requires the separate service secret. Do not expose that secret to clients.

## WebSocket protocol

Connect directly to worker `/ws/transcribe`. Origin must exactly match `CORS_ORIGINS`. Obtain a ticket via REST, then send within 10 seconds:

```json
{"type":"auth","ticket":"one-use-ticket","title":"Live meeting"}
```

Wait for `{type:"ready",sample_rate:16000,max_duration:300}`. Send binary **signed little-endian PCM16, mono, 16000 Hz**, at most 32000 bytes per frame. Do not send MediaRecorder WebM fragments as PCM. The frontend uses AudioWorklet and a 16 kHz AudioContext. JSON controls: `{type:"pause"}`, `{type:"resume"}`, `{type:"stop"}`. Flush audio before stop. Paused audio is ignored; pause time is excluded from duration. Idle sockets expire after 60 seconds; total wall time is bounded separately.

Server messages:

- `partial`: `text`, `language`, `duration`. Replace the displayed text with this snapshot.
- `final`: `text`, `language`, `record` (saved transcription including UUID). Sent only after DB commit; socket closes normally.
- `error`: `message` and available partial `text`. Client retains text for export/recovery. If audio was received, an interrupted session is saved as failed when the database is available.

Whisper is not a native streaming recognizer. This implementation uses 3-second windows and a 1-second retained overlap, offloads inference to one dedicated thread, and limits concurrent sessions to four per process. Prefix/suffix deduplication preserves Unicode marks and strips punctuation for matching. Overlap prevents common boundary duplication; model rephrasing, repetition and imperfect recognition can still require manual correction. `task=transcribe` avoids explicitly translating; code-switching quality and script choice depend on Whisper/model/audio. The language label is the model's most recent detected language, not a guarantee that every word belongs to it.

## Testing and checks

Use a development environment; automated tests mock Whisper and do not download weights.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check app transcription_worker scripts tests
python -m ruff format --check app transcription_worker scripts tests
python -m bandit -r app transcription_worker scripts -q
python -m pip_audit --progress-spinner off
python -m compileall -q app transcription_worker scripts
```

`requirements-dev.lock` records the exercised environment; `requirements.txt` pins REST direct dependencies. Worker dependencies and target OS/GPU wheels need their own resolved deployment lock and audit before release. To exercise real PostgreSQL, set `TEST_DATABASE_URL` to an **isolated test database**. Tests create/drop randomly named `test_<uuid>` schemas, never the public schema. The role needs schema create/drop privileges. Without that variable, tests use isolated temporary SQLite files. Test coverage includes CRUD ownership, filters, ticket expiry/replay/concurrency, CORS, audio validation, actual ASGI WebSocket routing with mocked inference, and resource cleanup.

Microphone smoke test (interactive, not part of pytest): install `sounddevice` in the worker environment, start both services, set `STT_ACCESS_TOKEN` to a provisioned user token, then run `python -m scripts.test_microphone --seconds 10`. The script records locally and sends PCM to the real worker. This verifies device, protocol and model together; automated mocks do not establish transcription accuracy.

## Production deployment

Documentation checked against official provider sources on 2026-11-25. Configurations are prepared; no cloud deployment or account has been created by this project.

1. **Neon:** create a project/database. Use the pooled hostname in `DATABASE_URL=postgresql+asyncpg://.../dbname`, without `sslmode`/`channel_binding` query parameters (these are not asyncpg keyword arguments). Set `DATABASE_SSL=true`; the engine passes a verified SSL context. `NullPool`, disabled statement caches and unique prepared statement names avoid holding serverless connections. Use a least-privilege application role, a separate schema administrator for `python -m app.db.init_db`, and Neon backups. [Neon SQLAlchemy guidance](https://neon.com/docs/guides/sqlalchemy), [Neon pooling](https://neon.com/docs/connect/connection-pooling).
2. **REST on Vercel:** import the repository, set Root Directory to `backend`, Python 3.12, and use FastAPI detection. `pyproject.toml` explicitly selects `app.main:app`. `.vercelignore` excludes worker source, tests, model/cache files, virtual environments and development tooling. Set the production env vars in Vercel, never in source. `APP_ENV=production` fails startup for a placeholder secret, missing DB TLS, HTTP worker URL or non-HTTPS origins. Do not run schema initialization in a build command. [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi).
3. **Worker on a traditional Python server (no Docker):** provision a private service account, Python 3.12, FFmpeg, enough RAM for the model, and optional CUDA. Check out `backend`, install worker requirements in a dedicated venv, set the same production database/key/CORS variables, and run `python -m uvicorn transcription_worker.main:app --host 127.0.0.1 --port 8001 --workers 1 --ws-max-size 32768 --ws-max-queue 8 --limit-concurrency 32` under systemd or another process supervisor. Put Nginx/Caddy with HTTPS/WSS in front. Configure WebSocket upgrade forwarding, at least 360-second upstream timeouts, a body limit just above 10 MiB, request-rate/IP connection limits and access-log redaction. Run FFmpeg/model code without elevated privileges. Restrict `/internal/audio` to the REST caller where possible. Each worker process has its own model and four-session admission limit; scale deliberately with hardware measurements.
4. **Optional Railway:** use `backend` as Root Directory, Railpack (no Dockerfile), override build to `pip install -r transcription_worker/requirements.txt`, install FFmpeg via `RAILPACK_DEPLOY_APT_PACKAGES=ffmpeg`, and set start command `python -m uvicorn transcription_worker.main:app --host 0.0.0.0 --port $PORT --workers 1 --ws-max-size 32768 --ws-max-queue 8 --limit-concurrency 32`. Configure health `/health`, model-cache volume and a startup timeout allowing weight loading. Validate available memory and FFmpeg on the deployed instance. [Railway build configuration](https://docs.railway.com/builds/build-configuration), [Railpack Python](https://railpack.com/languages/python/).
5. **Frontend:** deploy `frontend` as a separate Vercel project. Set public HTTPS API/WSS URLs and exact frontend origin in both Python services. The backend ticket response is authoritative for worker URLs. Vercel currently supports FastAPI WebSockets subject to function duration limits, but this application deliberately hosts sockets with the model on the persistent worker. Default Vercel request bodies are limited to 4.5 MB; a larger-body public beta exists on eligible plans. Direct worker uploads avoid depending on that beta. [Function limits](https://vercel.com/docs/functions/limitations).

Before public exposure configure Vercel Firewall/IP rate limiting for REST and equivalent proxy limits on the worker, including strict limits on unauthenticated traffic and ticket creation. App-level session bounds are per worker process, not a global distributed quota. A secret bearer token is appropriate for a provisioned private workspace, not a substitute for an enterprise SSO/account recovery system. Use HTTPS exclusively and privately distribute/rotate user tokens. CSP in the frontend should be tightened from `https:`/`wss:` to your exact service hosts.

Release gate: run all tests/checks, audit the **worker's resolved PyTorch/Whisper environment**, verify `/ready`, authenticate, record real English/Hindi/mixed audio, upload, edit, export and delete in staging. Test denial with a second user's token. Measure inference time against window duration under expected concurrency; lower concurrency or use a faster device/model if the worker falls behind. Monitor errors, active sessions, inference latency, CPU/RAM and DB connectivity. Hold release on missing save confirmations, privacy/ownership failures or unacceptable transcription quality. Roll back to the previous known application revision while preserving the database; `create_all` supplies no destructive rollback. Database backups have their own retention policy.

## Known limits

- No diarization, translation mode, native word-by-word streaming, reconnect/resume, durable job queue or cross-worker session migration.
- A process crash or database outage can lose unsaved audio; already received partial text remains in the browser while the page is open. Check history after a lost final acknowledgement before manually saving a recovery copy.
- File uploads run synchronously on the worker with bounded admission, not as durable queued jobs. Keep client/proxy timeouts compatible with your model's speed.
- Original Whisper can hallucinate on noise and struggle with names/code-switching. Silence gating is an energy threshold, not full voice activity detection. Review important transcripts.
- Text persists until the owner deletes it. Raw audio is transient; configure database backup retention and organizational consent policies for sensitive recordings.
- Real microphone/model quality, hosted TLS, proxy limits and provider account settings require deployment-specific acceptance checks; unit tests do not establish them.
