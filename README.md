# Daily Food

A food-first daily meal companion. The API applies allergy/diet rules and ranks curated starter recipes; the Next.js interface supports daily picks, meal discovery, preference editing, meal logging, and feedback. Nutrition values and recipe details in the starter catalog are explicitly labeled estimates.

## Current implementation and limits

- Frontend: Next.js 14, React, TypeScript, responsive App Router UI.
- API: FastAPI with versioned routes, input validation, request IDs, structured request logs, and local SQLite persistence.
- Data: small curated sample catalog. Supabase schema and row-level security migration are included, but the running API currently uses SQLite and does not connect to Supabase.
- Recommendation logic: deterministic eligibility and lightweight repetition/feedback ranking (`rules-v1`). Allergies filter both ingredient and known allergen labels.
- Auth and multi-user isolation are not implemented in the local API; do not expose this development deployment to the public internet. Supabase policies are a schema foundation, not evidence that API token verification is complete.
- NVIDIA NIM is configured server-side through `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, and `NVIDIA_MODEL`. Natural-language requests use Nemotron for intent parsing and explanations; Python re-applies all saved hard filters and serves deterministic results if NIM is unavailable.
- Prices are omitted because the curated records do not have defensible price sources. The budget field is stored but not yet used to rank.
- Images are remote Unsplash URLs. Attribution/source is recorded; availability and licensing are subject to those providers' terms.

## Requirements

Python 3.8+ and Node.js 18+ with npm or pnpm. Install Python packages and JS dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pnpm install
Copy-Item .env.example .env
```

If using npm, `npm install` is equivalent. Set `NEXT_PUBLIC_API_URL` in the frontend environment if the API is not at `http://localhost:8000`.

## Run locally

Copy `.env.example` to `.env.local` and place the NVIDIA key in that server-only file (never in a `NEXT_PUBLIC_` variable). The backend loads `.env.local`; the frontend does not.

In separate terminals from the project directory:

```powershell
python -m uvicorn backend.app:app --reload --port 8000
pnpm dev
```

Open http://localhost:3000. The SQLite file is created at `backend/foodrec.sqlite3` by default. Set `FOODREC_DB_PATH` to move it. API health is at http://localhost:8000/health and interactive docs at http://localhost:8000/docs.

## Checks

```powershell
python -m unittest discover -s tests -v
pnpm exec tsc --noEmit
pnpm build
```

## API

`GET /health`; `GET /api/v1/intelligence/status`; `POST /api/v1/intelligence/test`; `POST /api/v1/recommendations/ask` with `{ "request": "quick vegan dinner" }`; `GET/PUT /api/v1/preferences`; `GET /api/v1/foods?q=&category=`; `GET /api/v1/foods/{food_id}`; `GET /api/v1/recommendations/daily`; `POST /api/v1/recommendations/refresh`; `POST /api/v1/meals/log`; `GET /api/v1/nutrition/daily?day=YYYY-MM-DD`; `POST /api/v1/feedback`; `GET /api/v1/history?day=&meal_type=`.

## Supabase and production

`supabase/migrations/202610170001_initial.sql` establishes normalized user preferences, foods, recommendations, feedback and consumption with foreign keys, indexes, and RLS. Apply it only to a new or reviewed Supabase project. Wire verified Supabase JWT validation and the Supabase repository before enabling accounts or multi-user use. Keep service-role credentials on the server. Before production, implement/verify authentication, ownership checks in the API, rate limiting, database-backed catalog and event transactions, request logging redaction/retention, and browser/device QA. NIM provider errors are sanitized; usage request/error/latency counters are exposed without logging prompt bodies or credentials.
