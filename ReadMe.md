<div align="center">

<br/>

# 🌍 Conflict Tracker

### Real-time geopolitical intelligence, beautifully engineered.

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Redis](https://img.shields.io/badge/Upstash-Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![spaCy](https://img.shields.io/badge/spaCy-NLP-09A3D5?style=for-the-badge&logo=spacy&logoColor=white)
![Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

<br/>

> **Conflict Tracker** aggregates news from BBC, Reuters, Al Jazeera, GDELT, and more —
> then enriches every article with NLP sentiment analysis, named entity recognition,
> and geocoordinates. All in real-time, every 15 minutes.

<br/>

</div>

---

## ✨ What It Does

Conflict Tracker is a fully automated intelligence pipeline and REST API that:

- **Fetches** articles every 15 minutes from 6+ RSS feeds, NewsAPI, and GDELT 2.0
- **Cleans & deduplicates** every article before it touches the database
- **Geocodes** locations mentioned in articles to precise lat/lon coordinates
- **Classifies** articles into categories: military, diplomatic, economic, humanitarian, social
- **Runs NLP** — sentiment analysis via HuggingFace Transformers and named entity recognition via spaCy
- **Serves** all of this through a blazing-fast, rate-limited, Redis-cached REST API

---

## 🗺️ Architecture

<br/>

<div align="center">

### Pipeline Flow

![Pipeline Flow Diagram](screenshots/Pipeline%20flow%20diagram.png)

*Every 15 minutes: fetch → clean → deduplicate → geocode → NLP → store*

<br/>

### API Architecture

![API Architecture Diagram](screenshots/API%20architecture%20diagram.png)

*FastAPI + Supabase + Upstash Redis — deployed on Render*

</div>

<br/>

---

## 🚀 API Endpoints

Base URL: `https://conflict-tracker-api.onrender.com`

### Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/events` | Paginated list of events with full filtering |
| `GET` | `/events/map` | Geolocated events optimised for map rendering |
| `GET` | `/events/{id}` | Full event detail with sentiment & entities |

**Filters supported on `/events`:**

```
?category=military          # military | diplomatic | economic | humanitarian | social
?source=bbc                 # bbc | reuters | al_jazeera | gdelt | newsapi | ...
?from_date=2024-01-01       # ISO 8601 start date
?to_date=2024-12-31         # ISO 8601 end date
?geolocated=true            # Only events with lat/lon
?search=airstrike           # Full-text search across title & description
?limit=50&offset=0          # Pagination (max 200 per page)
```

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/sentiment-trend` | Daily avg sentiment score (last N days) |
| `GET` | `/analytics/category-breakdown` | Event counts grouped by category |
| `GET` | `/analytics/top-entities` | Most-mentioned named entities |
| `GET` | `/analytics/volume` | Daily event volume over time |
| `GET` | `/analytics/kpi` | Dashboard KPI tiles summary |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Full system health (DB + cache + pipeline) |
| `GET` | `/health/ping` | Simple liveness check — returns `pong` |

Interactive docs available at [`/docs`](https://conflict-tracker-api.onrender.com/docs) (Swagger UI) and [`/redoc`](https://conflict-tracker-api.onrender.com/redoc).

---

## 🔬 The Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                    Step 1 — Fetch                       │
│   RSS (BBC, Reuters, Al Jazeera, France24, Guardian)    │
│   + NewsAPI (10 conflict-focused search queries)        │
│   + GDELT 2.0 (15-minute event export, filtered)        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Step 2 — Clean                       │
│   Strip HTML · Decode entities · Normalise whitespace   │
│   Drop empty titles                                     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Step 3 — Deduplicate                    │
│   SHA-256 hash of title + URL                          │
│   Checked against DB + current batch                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Step 4 — Geocode                       │
│   Hardcoded known locations (50+ conflict hotspots)     │
│   → In-memory cache                                     │
│   → OpenCage Geocoding API                              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                 Step 5 — NLP Enrichment                 │
│   Category: keyword scoring across 5 categories         │
│   NER: spaCy en_core_web_sm — PERSON, ORG, GPE, NORP   │
│   Sentiment: HuggingFace cardiffnlp/twitter-roberta     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Step 6 — Write to DB                   │
│   Supabase (PostgreSQL) — events + sentiment + entities │
│   Rebuild sentiment_daily aggregation table             │
│   Log pipeline run metrics                              │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI 0.111 |
| **Database** | Supabase (PostgreSQL) |
| **Caching** | Upstash Redis (REST API) |
| **Rate Limiting** | SlowAPI (60 req/min per IP) |
| **Sentiment Analysis** | HuggingFace Inference API — `cardiffnlp/twitter-roberta-base-sentiment` |
| **Named Entity Recognition** | spaCy `en_core_web_sm` |
| **Geocoding** | OpenCage Geocoding API |
| **News Sources** | BBC, Reuters, Al Jazeera, France24, The Guardian, NewsAPI, GDELT 2.0 |
| **Deployment** | Render (web service) |
| **Logging** | Loguru |
| **Testing** | pytest + httpx + unittest.mock |

---

## 🏗️ Project Structure

```
conflict-tracker/
│
├── api/                        # FastAPI application
│   ├── main.py                 # App entry point, middleware, routers
│   ├── config.py               # Pydantic settings (env-driven)
│   ├── dependencies.py         # Supabase client, pagination params
│   ├── cache.py                # Upstash Redis caching layer
│   ├── middleware/
│   │   └── rate_limit.py       # SlowAPI rate limiter
│   ├── routers/
│   │   ├── events.py           # /events endpoints
│   │   ├── analytics.py        # /analytics endpoints
│   │   └── health.py           # /health endpoints
│   └── tests/
│       ├── conftest.py         # Shared fixtures & mock Supabase
│       ├── test_events.py
│       ├── test_analytics.py
│       └── test_health.py
│
├── pipeline/                   # Data ingestion pipeline
│   ├── run_once.py             # Entry point — runs one full cycle
│   ├── config.py               # All pipeline config & keywords
│   ├── fetchers/
│   │   ├── rss_fetcher.py      # BBC, Reuters, Al Jazeera, etc.
│   │   ├── newsapi_fetcher.py  # NewsAPI 10-query search
│   │   └── gdelt_fetcher.py    # GDELT 2.0 15-min export
│   ├── processors/
│   │   ├── cleaner.py          # HTML stripping, whitespace
│   │   ├── deduplicator.py     # Hash-based deduplication
│   │   ├── geocoder.py         # Location extraction + geocoding
│   │   ├── categorizer.py      # Keyword-based classification
│   │   ├── sentiment.py        # HuggingFace sentiment analysis
│   │   └── ner.py              # spaCy NER
│   ├── db/
│   │   ├── supabase_client.py  # Singleton DB client
│   │   └── writer.py           # All DB write operations
│   └── tests/
│       ├── test_cleaner.py
│       └── test_sentiment.py
│
├── screenshots/                # Architecture diagrams
├── requirements.txt
├── render.yaml                 # Render deployment config
├── Procfile
└── .env.example
```

---

## ⚡ Getting Started

### Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [HuggingFace](https://huggingface.co) account (free inference API)
- An [Upstash](https://upstash.com) Redis database (free tier)
- An [OpenCage](https://opencagedata.com) API key (free tier)
- A [NewsAPI](https://newsapi.org) key (free tier)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/conflict-tracker.git
cd conflict-tracker

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-key

# HuggingFace
HF_API_TOKEN=hf_your_token

# NewsAPI
NEWSAPI_KEY=your_newsapi_key

# OpenCage
OPENCAGE_KEY=your_opencage_key

# Upstash Redis
UPSTASH_REDIS_REST_URL=https://your-db.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token
```

### 3. Run the Pipeline

```bash
# Run one full pipeline cycle
python -m pipeline.run_once
```

### 4. Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

API is now live at `http://localhost:8000` · Docs at `http://localhost:8000/docs`

### 5. Run Tests

```bash
pytest api/tests/ pipeline/tests/ -v --cov=api --cov=pipeline
```

---

## 🌐 Deployment

The API is configured for one-click deployment on **Render**:

```bash
# render.yaml handles everything:
# - pip install -r requirements.txt
# - python -m spacy download en_core_web_sm
# - uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Set your environment variables in the Render dashboard — the `render.yaml` defines all required keys.

The pipeline runs via **GitHub Actions** on a 15-minute schedule:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'
```

---

## 🔒 Rate Limiting & Caching

| Concern | Configuration |
|---------|--------------|
| Rate limit | 60 requests/minute per IP (SlowAPI) |
| Events cache TTL | 2 minutes |
| Map cache TTL | 5 minutes |
| Analytics cache TTL | 10 minutes |
| Health cache TTL | 30 seconds |
| Max page size | 200 results |

Caching degrades gracefully — if Redis is unavailable, the API continues serving requests directly from Supabase.

---

## 📊 Data Model

```
events              → Core article data (title, url, published_at, lat, lon, category, ...)
  └── sentiment     → HuggingFace sentiment score & label (1:1 with event)
  └── entities      → spaCy named entities (1:N with event)

sentiment_daily     → Daily aggregation table (rebuilt each pipeline run)
pipeline_runs       → Audit log of each pipeline execution
```

---

## 📡 Data Sources

| Source | Type | Update Frequency |
|--------|------|-----------------|
| BBC World / Middle East | RSS | On publish |
| Reuters World News | RSS | On publish |
| Al Jazeera | RSS | On publish |
| France 24 | RSS | On publish |
| The Guardian World | RSS | On publish |
| NewsAPI | REST API | Every 15 min |
| GDELT 2.0 | CSV export | Every 15 min |

All sources are filtered by a curated list of **conflict keywords** before storage, keeping the database focused on geopolitical events.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

```bash
# Run the full test suite before submitting
pytest api/tests/ pipeline/tests/ -v
```

---

<div align="center">

<br/>

Built with care for understanding the world better.

<br/>

![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=flat-square&logo=python&logoColor=white)
&nbsp;
![Powered by spaCy](https://img.shields.io/badge/Powered%20by-spaCy-09A3D5?style=flat-square)
&nbsp;
![Data from GDELT](https://img.shields.io/badge/Data%20from-GDELT-FF6B35?style=flat-square)

</div>