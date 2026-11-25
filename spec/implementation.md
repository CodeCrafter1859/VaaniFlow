# Speech to Text v1

Build order: authenticated persistence → REST CRUD/statistics → bounded Whisper worker → React recording/history → verification and release documentation.

The existing request is the approved specification. REST and worker share SQLAlchemy models, configuration and owner-scoped repositories; only the worker imports Whisper/PyTorch. Provisioned random bearer tokens are stored as SHA-256 digests; the browser holds a token only in memory. Single-use database-backed tickets authorize worker sockets/uploads without exposing service credentials. Additional owner and ticket tables are required for isolation. No public registration is provided.

Acceptance: CRUD is owner isolated, validated and paginated; stats use real records; audio is bounded and decoded locally; 16 kHz PCM windows overlap and deduplicate; stop persists before acknowledgement; failed/disconnected sessions are recorded; inference runs in a bounded thread executor. UI supports accessible responsive navigation, themes, live capture controls, exports and history editing. No synthetic dashboard data.

Contracts: successful JSON `{data: ...}`, failures `{error: {code, message}}`. REST bearer authentication; WebSocket first frame `{type: "auth", ticket}` then binary little-endian signed PCM16 mono at 16000 Hz, JSON pause/resume/stop; server ready/partial/final/error. Full transcript snapshots replace client text, never append. Terminal final includes saved record ID. Partial text is provisional.

Verification: pytest integration tests (SQLite isolated adapter plus PostgreSQL when available), mocked model tests, Vitest/Testing Library, TypeScript build, oxlint, Ruff, Bandit, pip-audit and npm audit. Real microphone, Whisper quality and hosted smoke checks must be explicitly distinguished from mocks.

Deployment: frontend and REST on Vercel; persistent worker on a traditional Python host (no containers needed), optional Railway Railpack. 10 MB uploads go directly to worker via a short-lived ticket because Vercel requests are capped. No deployment or cloud account is assumed available. PostgreSQL create_all initializes schema only; future changes need reviewed SQL.
