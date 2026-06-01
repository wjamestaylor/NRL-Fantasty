# NRL-Fantasty

MVP implementation for a **Fantasy NRL Trade Lab** with:

- **Frontend:** Next.js + TypeScript + Tailwind (`/frontend`)
- **Backend:** FastAPI analytics API (`/backend`)

## Roadmap

### Phase 1 — MVP foundation
- [x] Home dashboard
- [x] Trade Lab screen
- [x] Player Research screen
- [x] Planner screen
- [x] News & Alerts screen
- [x] FastAPI backend with initial endpoints
- [x] Trade scoring framework
- [x] Sample recommendation payloads and workflows

### Phase 2 — Real data integration
- [ ] Replace placeholder/sample data with real player, fixture, and news feeds
- [ ] Add player prices, averages, rolling scores, minutes, and projections
- [ ] Add breakeven support when a reliable feed is available
- [x] Persist historical player and fixture snapshots
- [ ] Add source health monitoring for data ingestion

### Phase 3 — Team-aware recommendations
- [ ] Manual squad builder and editable roster management
- [ ] Bank, trades remaining, and boost tracking
- [ ] Locked players / must-sell player controls
- [ ] Best 1-, 2-, and 3-trade recommendation engine
- [ ] Explain recommendations with projected points, cash impact, and risk

### Phase 4 — Planning and optimization
- [ ] Bye-round coverage planner
- [ ] Cash generation and price-change planning
- [ ] Scenario modes: conservative, balanced, aggressive
- [ ] Multi-round trade simulations
- [ ] Position flexibility and squad structure scoring

### Phase 5 — News and risk intelligence
- [ ] Automated team list and injury signal ingestion
- [ ] Origin/rest risk tracking
- [ ] Role change detection
- [ ] Coach/news sentiment flags
- [ ] Confidence scores on recommendations

### Phase 6 — Product polish
- [ ] Navigation shared across all screens
- [ ] Mobile-first responsive UX improvements
- [ ] Saved user teams
- [ ] Authentication
- [ ] Visual charts for trends, projections, and planning
- [ ] Deployment, CI, and production monitoring

## Backend (FastAPI)

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### API endpoints

- `GET /players`
- `GET /players/analytics`
- `GET /players/{id}`
- `GET /players/{id}/analytics`
- `GET /fixtures`
- `GET /news/signals`
- `POST /user-team/import`
- `POST /trade/recommend`
- `POST /trade/simulate`
- `GET /planner/bye`
- `GET /health/data-sources`
- `GET /history/snapshots`
- `GET /history/snapshots/{dataset}/{date}`

## Historical snapshot archiving

Each time `refresh_snapshots_from_live_feeds()` runs, the validated payloads are also archived to:

```
backend/data/archive/<dataset>/<YYYY-MM-DD>.json.gz
```

One gzip-compressed file is written per dataset per calendar day (UTC).  A second refresh on the same day overwrites the earlier file, so the archive always reflects the latest intra-day state.

### Supported datasets

| Dataset | Archive path |
|---------|-------------|
| `players` | `data/archive/players/YYYY-MM-DD.json.gz` |
| `fixtures` | `data/archive/fixtures/YYYY-MM-DD.json.gz` |
| `news` | `data/archive/news/YYYY-MM-DD.json.gz` |

### Custom archive location

Set `NRL_ARCHIVE_DIR` to override the default archive root directory.

### Querying historical archives

```
GET /history/snapshots                          -> list available dates per dataset
GET /history/snapshots/{dataset}/{YYYY-MM-DD}   -> return archived payload for that date
```

### Retention and pruning

Use `archive.prune_archive(data_dir, dataset, keep_days=90)` to remove entries older than a given number of days.  Recommended to run as a periodic maintenance task alongside the daily refresh.

### GDPR — right to erasure

To remove all historical records for a specific player across every players archive:

```python
from pathlib import Path
from app.archive import purge_player_from_archives

purge_player_from_archives(Path("backend/data"), player_id="<player-id>")
```

This rewrites affected archive files in-place without deleting other players' data.

## Data feeds and ingestion

The backend now loads player, fixture, and news data from configurable live feeds with a validated historical snapshot fallback.

- `NRL_PLAYERS_FEED_URL` -> live player stats feed (JSON array of `Player` objects, optional `breakeven` per player)
- `NRL_FIXTURES_FEED_URL` -> live fixture feed (JSON array of `Fixture` objects)
- `NRL_NEWS_FEED_URL` -> live news/alerts feed (JSON array of `NewsSignal` objects)
- `NRL_PLAYER_PRICE_HISTORY_FEED_URL` -> optional live player price history feed
- `NRL_PLAYER_GAME_DETAILS_FEED_URL` -> optional live player per-game detail feed

If any live source is unavailable, the API automatically falls back to validated historical snapshots:

- `backend/data/players_snapshot.json`
- `backend/data/fixtures_snapshot.json`
- `backend/data/news_snapshot.json`
- `backend/data/player_price_history_snapshot.json`
- `backend/data/player_game_details_snapshot.json`

Breakeven support is automatically enabled only when every loaded player has `breakeven` populated. If coverage is incomplete, breakeven is disabled and omitted from player payloads to avoid partial/incorrect insight.

You can refresh snapshots from live feeds for full-season coverage and late changes using:

```bash
cd backend
NRL_PLAYERS_FEED_URL="https://<players-feed>" \
NRL_FIXTURES_FEED_URL="https://<fixtures-feed>" \
NRL_NEWS_FEED_URL="https://<news-feed>" \
python -m app.feed_ingestion
```

Recommended production automation:
- schedule snapshot refresh at least daily during the season
- add an extra run shortly after team-list announcements (typically Tuesday evening AEST) to capture late role/injury changes

Feature capability is exposed at `GET /health/data-sources` under:

- `features.player_breakeven.enabled`
- `features.player_breakeven.reason`
- `features.player_breakeven.coverage`

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

Set `NRL_API_BASE_URL` in `frontend` to enable server-side feature checks (including conditional breakeven visibility on `/player-research`).

## Tests

```bash
cd /tmp/workspace/wjamestaylor/NRL-Fantasty/backend
pytest
```
