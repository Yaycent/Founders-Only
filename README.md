# Founders-Only

React + Vite frontend with a Python FastAPI backend. Authentication and account data use a local SQLite database; email verification, OTP, password reset, and social login are intentionally not included.

## Requirements

- Node.js 20.19+ or 22.12+
- Python 3.12 (Windows Python Launcher `py`)
- npm

## Configure and run

Install frontend dependencies:

```powershell
npm install
```

Create and prepare the Python environment:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Create `backend/.env` from `backend/.env.example` if needed. Set `JWT_SECRET` to a private random value of at least 32 characters. This file is ignored by git; do not put secrets in Vite or frontend environment variables.

Run the Python API in one terminal:

```powershell
npm run dev:server
```

Run the frontend in a second terminal:

```powershell
npm run dev
```

Open `http://localhost:3001`. Vite proxies `/api` requests to the API on port `4000`.

## Authentication and data

- Create an account at `/register`, or sign in at `/login`.
- Passwords are stored as bcrypt hashes. Passwords are never returned by the API.
- JWT sessions are HttpOnly, SameSite Strict cookies. The JWT secret stays in `backend/.env`.
- All application routes require a valid session. Account APIs validate the JWT and select data by the authenticated user's ID.
- User credentials and account profile/preferences are stored in `backend/data/founders_only.sqlite3`.
- The inbox and briefing remain fictional mock content; no email provider or AI service is connected.

## API

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me` (protected)
- `GET /api/account` (protected)
- `PATCH /api/account` (protected)
- `GET /api/health`

Build the frontend with `npm run build`.

Run isolated authentication integration checks with `npm run test:auth`. The test starts a temporary Python backend using its own temporary SQLite file, then removes the temporary data.
