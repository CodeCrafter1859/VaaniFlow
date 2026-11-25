# Speech to Text frontend

React + Vite + TypeScript, Tailwind CSS, Lucide icons and React Router. Uses native Fetch through `src/services/api.ts` and the browser's native WebSocket API. Dashboard and history are fetched from the backend; no sample records are shipped.

## Install and run

For the complete local app, run **`python run.py` from `backend/`**. It also starts this frontend and installs missing dependencies. Follow the [one-command setup](../backend/README.md#start-everything-locally-with-one-command) for prerequisites. The instructions below are for running only the frontend independently.

Use Node.js 22.19+ and npm. From `frontend/`:

```bash
npm ci
cp .env.example .env
npm run dev
```

On Windows PowerShell use `npm.cmd` if execution policy blocks `npm.ps1`, and `Copy-Item .env.example .env` instead of `cp`. `.npmrc` disables install scripts; the tested Vite installation uses published platform binaries without lifecycle scripts. Open `http://localhost:5173`.

`.env` contains **public configuration only**:

```dotenv
VITE_APP_NAME="Speech to Text"
VITE_APP_ENV=development
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8001/ws/transcribe
```

All `VITE_` values are public in the compiled bundle. For local shared testing only, set `VITE_ENABLE_TEST_LOGIN=true` and `VITE_TEST_ACCESS_TOKEN` to the same random token configured as backend `TEST_ACCESS_TOKEN`. The frontend token is compiled into browser JavaScript, so this one-click test login is only safe on localhost or another restricted test environment; never set it in a public production Vercel project. Keep production testing on individual private access tokens. Never place a database URL, service key, or user token here. Actual `.env` files are ignored; `.env.example` is the checked-in template. Rebuild after changing production variables. The authenticated ticket response supplies the authoritative worker URL, configured with `TRANSCRIPTION_WEBSOCKET_URL` on the backend; keep `VITE_WS_URL` aligned with it.

Start REST on port 8000 and the worker on port 8001. Backend installation, PostgreSQL `create_all()` initialization, original Whisper dependencies, FFmpeg installation, environment configuration and separate-worker startup commands are in [backend/README.md](../backend/README.md). No FFmpeg or model package runs in the browser. Provision a user using `python -m scripts.create_user "Your name"` from the backend environment and enter the resulting token at sign-in. Tokens remain in memory; reload/sign-out clears access. There is no anonymous/default-user bypass.

## Features and flow

- Overview: actual counts, total duration, recent records and language distribution, with empty/loading/error states.
- Live: microphone permission handling, start/pause/resume/stop, actual microphone frequency visualization, sample-based timer, connection status, auto language detection, partial snapshots and final save acknowledgement.
- AudioWorklet captures signed PCM16 at 16 kHz. The final worklet frame is flushed before stop/pause. Audio tracks and contexts are released on stop, error or unmount.
- Stop saves on the worker before displaying “Saved.” Copy/download are always available for received text. Save is for recovering an unsaved partial result; it does not duplicate an already acknowledged record. Clear resets the local view and does not delete history.
- Upload: supported audio up to 10 MiB/5 minutes; obtains a one-use upload ticket and sends directly to the worker. No service key enters the browser.
- History: title/text search, language/status filters, sorting, pagination, full-text view/edit, copy/download and modal delete confirmation. Native dialogs trap keyboard focus and support Escape.
- Responsive sidebar, light/dark theme (only the theme preference is in localStorage), accessible control labels, reduced-motion styling and toast messages.

## API and WebSocket

`request<T>(path, token, options)` adds the bearer header, serializes no hidden data, preserves FormData boundaries, unwraps `{data: ...}`, handles structured/non-JSON failures and supports cancellation. Endpoints and wire format are documented in the [backend contract](../backend/README.md#rest-contract). Private requests require a provisioned token.

Recording obtains `POST /api/v1/auth/ticket`, opens the returned WebSocket URL, authenticates in the first frame (not a query string), waits for `ready`, then sends binary PCM. Incoming `partial` snapshots replace text; `final` contains the persisted record. No automatic reconnect is attempted because replaying audio could duplicate records. On unexpected disconnect, check history before saving a recovery copy. Browser buffering is bounded; long-running inference also requires worker-side capacity planning.

## Tests, type checks and build

```bash
npm test
npm run lint
npm run build
npm audit --audit-level=moderate
npm run preview
```

`build` runs TypeScript project checks and Vite's production bundle. Vitest + React Testing Library tests cover Fetch behavior, login failure, API-backed dashboard/history editing, delete confirmation, microphone denial and mocked recording lifecycle. Mock responses exist only under `tests/`; these tests do not verify microphone hardware, actual Whisper accuracy, browser rendering or cloud deployment. `npm run format` applies Prettier. See [verification report](../verification/RESULTS.md) for actual observed results.

## Vercel deployment

Create a Vercel project with Root Directory `frontend`, Framework Vite, build `npm run build`, output `dist`. `vercel.json` defines SPA rewrites and security headers. Set `VITE_API_BASE_URL=https://your-rest-host/api/v1` and `VITE_WS_URL=wss://your-worker-host/ws/transcribe`, then rebuild. Set both Python services' `CORS_ORIGINS` to the exact frontend HTTPS origin. Preview deployments need their own explicit allowed origins; do not allow a wildcard.

Use HTTPS/WSS; microphone access works only on secure origins or localhost. Narrow `connect-src` in the CSP to your REST/worker hosts before production exposure. Keep `pcm-worklet.js` available as JavaScript, not an SPA HTML fallback. Test a direct `/history` navigation after deployment. [Official Vite deployment on Vercel](https://vercel.com/docs/frameworks/frontend/vite), [Vercel project configuration](https://vercel.com/docs/project-configuration).

Before release, test desktop/mobile layouts and keyboard navigation in your supported browsers, permit/deny microphone access, record English/Hindi/mixed phrases, pause/resume, stop/save, upload and edit/delete as two different users. Verify CORS/WSS and error recovery when the worker is offline. Roll back to a known frontend deployment if the critical recording/save flow fails; frontend deployments do not alter database schema.

## Limitations

- Requires a modern browser with AudioWorklet and 16 kHz AudioContext support. Unsupported capture rates show an error; file upload remains available.
- Pauses longer than the worker idle timeout (60 seconds) disconnect. Maximum recording duration is supplied by the worker; default UI copy describes the shipped 5-minute/10 MiB limits.
- Switching away from Live releases microphone resources and closes its socket; partial text is local to that page. Stop/save before navigating or signing out.
- No session restoration across reloads, speaker identification, offline transcription, or guaranteed verbatim mixed-language recognition. Edit important transcripts after recording.
- Hosted services, real microphone capture and actual Whisper quality need separate staging acceptance checks.
