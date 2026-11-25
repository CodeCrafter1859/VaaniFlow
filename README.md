# Real-time multilingual Speech to Text

Private English/Hindi/mixed-language transcription using React, FastAPI, PostgreSQL and self-hosted original OpenAI Whisper. REST/frontend deploy independently; inference and WebSockets run on a persistent Python worker. No paid transcription APIs, Docker or Alembic.

- [Backend and worker setup, API, database and deployment](backend/README.md)
- [Frontend setup and recording workflow](frontend/README.md)
- [Implementation specification](spec/implementation.md)
- [Verification evidence and remaining release gates](verification/RESULTS.md)

For local development, run `python run.py` from `backend` to install missing project dependencies, create a missing database, initialize tables and launch REST, Whisper and the frontend together. Open http://localhost:5173. PostgreSQL must be running with valid credentials configured in `backend/.env`; Python, Node/npm and FFmpeg must be installed. See the backend README for one-time setup. Both projects include ignored `.env` files and tracked `.env.example` templates. Production services remain independently deployable.
