# When Will You Die?

A full-stack app that estimates a statistical death date from country-level public data (life expectancy, income, education, ethnicity, weather) and personal factors.

- **Backend:** Python 3 + FastAPI (serverless on Vercel)
- **Frontend:** React + TypeScript (Vite)
- **Periodic tasks:** Vercel Cron refreshes country data daily

> **Disclaimer:** This is a statistical toy, not medical advice.

## Project structure

```
api/              Python FastAPI handlers (Vercel serverless)
data/             Seed cache for countries
frontend/         React + TypeScript UI
scripts/          Local dev helpers
vercel.json       Vercel build, rewrites, cron
requirements.txt  Python dependencies
```

## Local development

### 1. Python API (with venv)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run API on http://127.0.0.1:8000
./scripts/dev-api.sh
# or: uvicorn api.index:app --reload --host 127.0.0.1 --port 8000
```

### 2. Refresh country data (optional)

```bash
source venv/bin/activate
./scripts/refresh-data.sh
```

This fetches data from World Bank, REST Countries, and Open-Meteo, then writes `data/cache.json`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to the Python backend.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Service health + cache info |
| GET | `/api/countries` | List cached countries |
| GET | `/api/countries/{code}` | Country stats (life, income, education, ethnicity, weather) |
| POST | `/api/predict` | Death date estimate from your profile |
| GET | `/api/cron/fetch-data` | Cron job: refresh all country data |

### Predict request example

```json
{
  "birth_date": "1990-06-15",
  "gender": "female",
  "country_code": "US",
  "education": "tertiary",
  "income_level": "average",
  "activity_level": "moderate",
  "smoking": "never"
}
```

## Deploy to Vercel

### Automatic deploys (every push)

Use [Vercel's GitHub integration](https://vercel.com/docs/git/vercel-for-github) — no GitHub Actions secrets required.

**One-time setup**

1. Go to [vercel.com/new](https://vercel.com/new) and import `lisss/dday` from GitHub.
2. Leave build settings as-is (they come from `vercel.json`).
3. Deploy. Vercel will deploy on every push:
   - `main` → production
   - other branches → preview

If the project already exists on Vercel, connect the repo under **Project → Settings → Git**.

### Manual deploy

```bash
vercel
vercel --prod
```

### Environment variables

Optional: set `CRON_SECRET` in the Vercel dashboard (Project → Settings → Environment Variables) to secure the cron endpoint.

The cron job runs daily at 06:00 UTC (`0 6 * * *`) and refreshes data for 20 countries.

### Notes on Vercel

- Python functions live in `api/index.py` (FastAPI `app`).
- Static frontend is built from `frontend/` into `frontend/dist`.
- Serverless `/tmp` cache is ephemeral; seed data in `data/countries_seed.json` is used as fallback until cron runs.
- Hobby plan: up to 2 cron jobs, minimum once per day.

## Data sources

- [World Bank Open Data](https://data.worldbank.org/) — life expectancy, GDP per capita, school enrollment
- [REST Countries](https://restcountries.com/) — country metadata
- [Open-Meteo](https://open-meteo.com/) — current weather (no API key)
- Ethnicity breakdowns — curated public demographic summaries for major countries
