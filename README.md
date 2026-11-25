# Real-time multilingual Speech to Text

Private English/Hindi/mixed-language transcription using React, FastAPI, PostgreSQL and self-hosted original OpenAI Whisper. REST/frontend deploy independently; inference and WebSockets run on a persistent Python worker. No paid transcription APIs, Docker or Alembic.

- [Backend and worker setup, API, database and deployment](backend/README.md)
- [Frontend setup and recording workflow](frontend/README.md)
- [Implementation specification](spec/implementation.md)
- [Verification evidence and remaining release gates](verification/RESULTS.md)

Start with backend database initialization and user provisioning, run REST on `8000`, worker on `8001`, then `npm run dev` in `frontend`. Both projects include ignored `.env` files and tracked `.env.example` templates. A working PostgreSQL connection, FFmpeg and worker model installation are required for actual transcription.
