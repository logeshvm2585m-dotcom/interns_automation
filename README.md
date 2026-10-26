# InternFlow AI

InternFlow AI is a local-first internship review automation system. It runs with SQLite and explicit demo integrations when external credentials are unavailable.

## Run locally

### Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The backend API is available at http://localhost:8000/docs.

Set `DEMO_MODE=false` only when OAuth and provider credentials have been configured. Demo email, calendar, and AI operations are clearly labelled and never contact external services.
