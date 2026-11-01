# Founders-Only

A frontend-only executive email experience built with React, Vite, React Router, and mock business data. No email provider, AI service, or backend is connected.

## Requirements

- Node.js 20.19+ or 22.12+
- npm

## Run locally

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
npm run dev
```

Open the local URL printed by Vite. To create a production build:

```bash
npm run build
npm run preview
```

## Included screens

- Dashboard with correspondence, agenda, priority matters, and portfolio overview
- Executive Identity with editable profile details
- Intelligent Inbox with mock messages, category filters, search, read status, and importance flags
- AI Reply Studio with style/action-driven mock responses, editable drafts, copy, and send confirmation
- Daily Briefing with schedule, tasks, deadlines, opportunities, and delivery preferences
- Settings with locally persisted profile and preferences

Profile and preference changes are stored in this browser using `localStorage`. All email and briefing content is fictional and static.
