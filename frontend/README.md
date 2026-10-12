# Search-Grounded AI Agent Drift Gate - Frontend

## Overview

The frontend lets users inspect captured search evidence, compare baseline and current captures, and review offline replay results.

## Requirements

- Node.js and npm
- A running, reachable backend API
- Accessible capture data for comparison and replay

## Setup

From the repository root, run:

```powershell
cd frontend
npm install
```

Create or update `frontend/.env.local` with the backend API URL:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Replace the example URL with the actual reachable backend address. If the backend runs on another laptop, use its LAN IP address and port. The backend must allow connections from the frontend machine.

Restart the development server after changing `.env.local`.

Keep `SERPAPI_KEY` and other private credentials on the backend. Never expose them in frontend code.

## Run locally

From the `frontend` directory, run:

```powershell
npm run dev
```

Open http://localhost:3000.

## Main pages

- `/` - Dashboard
- `/captures` - Capture history
- `/captures/[id]` - Capture details and saved evidence
- `/compare` - Compare captures and persist evaluations
- `/replay` - Offline replay workflow

Results depend on the configured backend API and its stored data.

## Validation

From the `frontend` directory, run:

```powershell
npm run lint
npm run build
```

Both commands should complete successfully before handoff.

## Backend integration checklist

Verify these behaviors against the intended backend:

1. Identical persisted-evaluation retries return the existing evaluation without creating a duplicate.
2. An edited claim or evidence selection uses a new answer revision ID and creates a distinct evaluation.
3. API errors are displayed clearly.
4. Capture details and offline replay work with the integrated backend.

Do not delete existing persisted evaluation records during testing.

## Environment and security

- Do not commit `.env.local`.
- `NEXT_PUBLIC_API_URL` is public client-side configuration, not a secret.
- Search provider API keys must remain on the backend.
