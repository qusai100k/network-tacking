# NetVision AI

A local desktop network monitoring prototype. The Electron app displays devices, processes, and connections from a FastAPI backend, which also streams live telemetry over WebSockets.

## Repository layout

| Path | Purpose |
| --- | --- |
| `apps/desktop/` | Electron shell and React/TypeScript dashboard |
| `apps/backend/` | FastAPI routes, monitoring runtime, and SQLite storage |

## Run locally

Install Node.js with npm and Python. Create and activate a Python virtual environment, then run these commands from the repository root:

```sh
python -m pip install -r apps/backend/requirements.txt
npm ci
npm run dev
```

The development script starts FastAPI at `http://127.0.0.1:8000` and opens the Electron dashboard. Vite serves the dashboard at `http://127.0.0.1:5173`.

## API entry points

- `GET /health` checks backend health.
- `GET /api/v1/bootstrap` returns the initial dashboard data.
- `GET /api/v1/devices`, `/api/v1/processes`, and `/api/v1/connections` return individual views.
- `GET /api/v1/ai/analysis` and `POST /api/v1/ai/chat` expose analysis and chat.
- `WS /ws/telemetry` streams monitoring updates.
