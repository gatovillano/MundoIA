# Copilot Instructions for MundoIA

## Build, Test, and Lint Commands

### Backend (Python)
- **Install dependencies:**
  ```bash
  pip install -r requirements.txt
  ```
- **Run server (dev):**
  ```bash
  uvicorn api.api:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Run with Docker Compose:**
  ```bash
  docker-compose up --build
  ```
- **Run a single test:**
  ```bash
  pytest tests/test_evolutive_skills.py -v
  ```
- **Run all tests:**
  ```bash
  pytest tests/
  ```
- **Lint (Python):**
  ```bash
  ruff .
  # or
  flake8 .
  ```

### Frontend (web/frontend)
- **Install dependencies:**
  ```bash
  npm install
  ```
- **Dev server:**
  ```bash
  npm run dev
  ```
- **Build:**
  ```bash
  npm run build
  ```
- **Lint:**
  ```bash
  npm run lint
  ```
- **Test (if available):**
  ```bash
  npm test
  ```

### Mobile (mobile/android_app/android_expo)
- **Install dependencies:**
  ```bash
  npm install
  ```
- **Start app:**
  ```bash
  npm run start
  # or
  npx expo start
  ```
- **Lint:**
  ```bash
  npm run lint
  ```

## High-Level Architecture

- **Backend:** FastAPI (Python), PostgreSQL, LangGraph, WebSocket, modular core in `core/` and `agents/`.
- **Frontend:** Next.js (React 19, Zustand, D3.js, Three.js), in `web/frontend/`.
- **Mobile:** Expo/React Native in `mobile/android_app/android_expo/`.
- **Dockerized:** `docker-compose.yml` orchestrates DB, backend, frontend.
- **Key modules:**
  - `core/modelo.py`: Main simulation logic (to be refactored into modules)
  - `core/world_system.py`, `core/utils.py`, `agents/`: Agent logic, world, skills
  - `api/api.py`: FastAPI app, WebSocket, session management
  - `tests/`: Python tests
  - `docs/`: Technical docs, dev changelog (`Cambios.md`), technical review

## Key Conventions

- **Changelog:** All significant changes must be documented in `docs/Cambios.md` (see its format).
- **Todos & Priorities:** Use `docs/TODO_ACCIONES.md` for prioritized tasks, with unique codes (e.g., WS-1, DB-1). Mark completed tasks and update priorities here.
- **Refactoring:** Large files (e.g., `modelo.py`) are being split into modules as per `TODO_ACCIONES.md`.
- **Testing:** New features should include unit/integration tests in `tests/`.
- **Frontend state:** Use Zustand store (`useGameStore.ts`) for global state.
- **WebSocket:** Only send deltas, not full state, to avoid bandwidth issues (see TODO WS-1).
- **Database:** Use indices as described in `TODO_ACCIONES.md` for performance.
- **Environment:** Use `.env` for config; see README for required variables.
- **Documentation:** Update `README.md` and `docs/REVISION_COMPLETA_FINAL.md` for major changes.

---

For more details, see `README.md`, `docs/TODO_ACCIONES.md`, and `docs/REVISION_COMPLETA_FINAL.md`.
