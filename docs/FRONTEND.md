# Frontend

React + TypeScript + Vite + Tailwind in `frontend/`.

## Env

```text
VITE_API_BASE_URL
VITE_WS_URL
```

## Pages

Login, Dashboard, Live Monitoring, Persons, Person Detail, Timeline, Search, Cameras, Topology, Behavior, Anomalies, Crowd, System Health, Admin.

Pages call FastAPI only through `src/api/client.ts`. Empty/unavailable backend capabilities show empty states — no fake data.

```bash
cd frontend
npm install
npm run dev
npm run build
```
