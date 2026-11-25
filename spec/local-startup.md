# Local startup convenience

`backend/run.py` is the local entrypoint. It runs REST, the model worker and Vite as supervised child processes, preserving independent production entrypoints and the Vercel dependency boundary.

Before starting: check system commands and available ports, copy missing env templates, bootstrap missing project environments, validate development settings, create the configured database only on PostgreSQL SQLSTATE 3D000, initialize tables and provision a random first-user token only when no user exists. Never overwrite existing envs/tokens, terminate unrelated processes, or assume OS/PostgreSQL administrator privileges. PostgreSQL service startup and FFmpeg installation remain one-time prerequisites. A missing database is created using existing configured credentials and privileges; lack of CREATEDB produces an actionable error. Database identifiers use dialect quoting, creation uses AUTOCOMMIT, and concurrent creation is resolved by reconnecting to verify the target.

Ready means all three health checks succeed. Failure, timeout or Ctrl+C stops owned children. Launch executable argv directly, without a shell or new visible windows. Vite runs via Node, avoiding npm wrapper descendants. Worker subprocess trees are cleaned up on shutdown.

Tests cover first-user idempotency, production refusal, preflight failure, direct service plans, launch-failure cleanup, sibling exit cleanup, real child termination and non-mutating help. Unchanged frontend/API behavior relies on the existing verification; new launcher behavior is validated separately. Full real-model startup is blocked until this machine has FFmpeg and worker dependencies.
