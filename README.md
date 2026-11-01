# Founders-Only

A frontend-only executive email experience built with React, Vite, React Router, and mock business data. No email provider, AI service, or backend is connected.

## Requirements

- Node.js 20.19+ or 22.12+
- npm

## Run locally

```bash
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
