# NRL-Fantasty

MVP implementation for a **Fantasy NRL Trade Lab** with:

- **Frontend:** Next.js + TypeScript + Tailwind (`/frontend`)
- **Backend:** FastAPI analytics API (`/backend`)

## Backend (FastAPI)

### Setup

```bash
cd /tmp/workspace/wjamestaylor/NRL-Fantasty/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### API endpoints

- `GET /players`
- `GET /players/{id}`
- `GET /fixtures`
- `GET /news/signals`
- `POST /user-team/import`
- `POST /trade/recommend`
- `POST /trade/simulate`
- `GET /planner/bye`
- `GET /health/data-sources`

## Frontend (Next.js)

```bash
cd /tmp/workspace/wjamestaylor/NRL-Fantasty/frontend
npm install
npm run dev
```

Available MVP screens:

- `/` Home dashboard
- `/trade-lab`
- `/player-research`
- `/planner`
- `/news`

## Tests

```bash
cd /tmp/workspace/wjamestaylor/NRL-Fantasty/backend
pytest
```
