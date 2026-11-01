# Founders-Only

Luxury business club dashboard with a React frontend and a Python FastAPI backend.
User accounts and account data are stored in a local SQLite database. Passwords
are bcrypt hashed, and the API uses an HttpOnly JWT cookie for sessions.

## Requirements

- Node.js 20.19+ or 22.12+
- Python 3.10+

## First-time setup (Windows PowerShell)

From the repository root:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Open `backend\.env` and replace `JWT_SECRET` with a private random value of at
least 32 characters. Keep that file local; it is ignored by Git.

To enable real AI reply generation, add your OpenAI credentials to
`backend\.env`:

```text
OPENAI_API_KEY=your_private_key
OPENAI_MODEL=gpt-4.1-mini
```

The key is read only by the Python backend. It is never sent to or bundled into
the frontend. Without a key, signup and the rest of the dashboard still run;
the Reply Studio shows a configuration error when generation is requested.

To load and reply to real inbox messages, also configure these backend-only
values in `backend\.env`:

```text
AGENTBOXD_API_KEY=your_private_agentboxd_key
AGENTBOXD_INBOX_ID=your_inbox_id
AGENTBOXD_ALLOWED_EMAIL=the_login_email_allowed_to_access_this_inbox
```

Inbox access and sending are protected by JWT and restricted to the configured
login email. The Reply Studio asks for confirmation before sending a message.

Install the frontend dependencies:

```powershell
cd frontend
npm install
```

Commit both `frontend\package-lock.json` and the backend requirements file when
updating dependencies so the whole team gets the same versions.

## Run in development

Use two terminals from the repository root.

Terminal 1, start the API:

```powershell
.venv\Scripts\python.exe backend\app.py
```

The API listens on `http://127.0.0.1:4000` and creates
`backend/data/founders_only.sqlite3` automatically.

Terminal 2, start the frontend:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3001`. Vite forwards `/api` requests to the API on port
4000. Sign up with an email and password, then the Dashboard opens. Logout
returns to the Login page.

## Production frontend build

```powershell
cd frontend
npm run build
```

The generated static files are placed in `frontend/dist/`.

## Project layout

```text
backend/
  app.py                 FastAPI routes, JWT sessions, and SQLite access
  requirements.txt       Python dependencies
  .env.example           Local backend configuration template
frontend/
  src/
    components/          Reusable dashboard components
    data/                Default dashboard content
    lib/                 API client
    pages/               Login, dashboard, inbox, and settings pages
    styles/              Global and component styles
  public/assets/         Dashboard imagery
```

The Dashboard's Canadian $100 note animation uses the profile's **Personal net
worth** to determine the number of notes, capped at 24. The notes are smaller
and fall faster; reduced-motion settings disable the animation.
