# Brew Analytics ☕

A full-stack business intelligence web application designed specifically for cafe businesses. Transforms raw transaction data into actionable insights through five analytical modules — KPI dashboard, market basket analysis, sentiment analysis, sales forecasting, and inventory management.

---

## Features

- **KPI Dashboard** — Revenue, orders, profit margin, hourly heatmap, customer retention, channel split
- **Market Basket Analysis** — FP-Growth algorithm discovers product associations and generates combo deal recommendations
- **Sentiment Analysis** — RoBERTa transformer model analyses Google and Zomato reviews with aspect-level breakdown
- **Sales Forecasting** — Facebook Prophet generates 30-day revenue forecasts with Mumbai holiday effects and confidence intervals
- **Inventory Management** — Stock alerts, depletion rates, Monday wastage spike detection, reorder suggestions
- **JWT Authentication** — Secure login with token-based access control on all API endpoints

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| ML — MBA | mlxtend (FP-Growth) |
| ML — Forecast | Facebook Prophet |
| ML — Sentiment | HuggingFace Transformers (RoBERTa) |
| Auth | python-jose (JWT) + bcrypt |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React.js + Vite |
| Routing | React Router v6 |
| Charts | Recharts |
| Styling | Custom CSS with CSS variables |

---

## Project Structure

```
CAFE BI TRIAL/
├── BACKEND/
│   ├── .env                        # DB credentials (not committed)
│   ├── main.py                     # FastAPI app + middleware + routers
│   ├── database.py                 # SQLAlchemy connection + session
│   ├── auth.py                     # JWT utilities + password hashing
│   ├── middleware.py               # Logging, rate limiting, caching, error handling
│   ├── generate_dataset.py         # Synthetic data generator
│   ├── create_user.py              # Admin user seeding script
│   ├── requirements.txt
│   ├── models/
│   │   └── kpi.py                  # SQLAlchemy table definitions
│   ├── routers/
│   │   ├── auth.py
│   │   ├── kpi.py
│   │   ├── mba.py
│   │   ├── inventory.py
│   │   ├── sentiment.py
│   │   └── forecasting.py
│   ├── schemas/
│   │   ├── kpi.py
│   │   ├── mba.py
│   │   ├── inventory.py
│   │   ├── sentiment.py
│   │   └── forecasting.py
│   └── services/
│       ├── kpi_service.py
│       ├── mba_service.py
│       ├── inventory_service.py
│       ├── sentiment_service.py
│       └── forecasting_service.py
│
└── cafe-bi-frontend/
    └── src/
        ├── App.jsx
        ├── api.js                  # All API fetch functions
        ├── main.jsx
        ├── index.css
        ├── hooks/
        │   └── useFetch.js
        ├── components/
        │   ├── Layout.jsx
        │   ├── Sidebar.jsx
        │   └── UI.jsx              # Shared components + helpers
        └── pages/
            ├── Login.jsx
            ├── Overview.jsx
            ├── KpiPage.jsx
            ├── MbaPage.jsx
            ├── SentimentPage.jsx
            ├── ForecastingPage.jsx
            └── InventoryPage.jsx
```

---

## Database Schema

Nine tables in `cafe_db`:

| Table | Rows | Purpose |
|---|---|---|
| `customers` | 3,000 | Customer segments and loyalty data |
| `menu_items` | 20 | Menu with prices and cost prices |
| `orders` | 19,691 | Transaction records with timestamps |
| `order_items` | 41,509 | Line items per order |
| `inventory` | 20 | Ingredient stock levels |
| `inventory_transactions` | 8,898 | Stock usage, restocks, wastage |
| `reviews` | 1,292 | Google and Zomato customer reviews |
| `weather_daily` | 366 | Daily Mumbai weather and holiday flags |
| `daily_sales_summary` | 366 | Pre-aggregated time series for Prophet |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 15
- pgAdmin (recommended for DB management)

---

### Backend Setup

**1. Clone the repository and navigate to the backend:**
```bash
cd "CAFE BI TRIAL/BACKEND"
```

**2. Create and activate a virtual environment:**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

> **Note:** Installing `prophet` and `transformers` will download large model files (~500MB) on first run. This is a one-time download.

**4. Create the database:**

Open pgAdmin and create a new database named `cafe_db`.

**5. Configure environment variables:**

Create a `.env` file in the BACKEND folder:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/cafe_db
```

**6. Generate synthetic data:**
```bash
python generate_dataset.py
```

This seeds all nine tables with ~75,000 records encoding realistic cafe patterns.

**7. Create the admin user:**
```bash
python create_user.py
```

Default credentials: `admin@brewanalytics.com` / `admin123`

**8. Start the backend server:**
```bash
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`.

> **Note:** On first startup, the RoBERTa sentiment model warms its cache in the background (~2 minutes). The server accepts requests immediately — sentiment endpoints serve from cache once warming completes.

---

### Frontend Setup

**1. Navigate to the frontend folder:**
```bash
cd "CAFE BI TRIAL/cafe-bi-frontend"
```

**2. Install dependencies:**
```bash
npm install
```

**3. Start the development server:**
```bash
npm run dev
```

The app runs at `http://localhost:5173`.

---

### Running Both Together

Open two terminals:

```bash
# Terminal 1 — Backend
cd "CAFE BI TRIAL/BACKEND"
.venv\Scripts\activate
uvicorn main:app --reload

# Terminal 2 — Frontend
cd "CAFE BI TRIAL/cafe-bi-frontend"
npm run dev
```

Open `http://localhost:5173` and log in with `admin@brewanalytics.com` / `admin123`.

---

## API Overview

All endpoints are prefixed with `/api` and require a JWT Bearer token except `/api/auth/login`.

| Module | Prefix | Endpoints |
|---|---|---|
| Authentication | `/api/auth` | 2 |
| KPI Dashboard | `/api/kpi` | 8 |
| Market Basket | `/api/mba` | 4 |
| Inventory | `/api/inventory` | 6 |
| Sentiment | `/api/sentiment` | 8 |
| Forecasting | `/api/forecast` | 5 |

Full interactive documentation available at `http://localhost:8000/docs` when the server is running.

---

## Middleware Stack

Requests pass through four middleware layers before reaching any route:

```
Request → ErrorHandler → RequestLogging → RateLimit → Cache → Route
```

| Middleware | Purpose |
|---|---|
| ErrorHandler | Returns clean JSON for any unhandled exception |
| RequestLogging | Logs method, path, status, and duration to terminal |
| RateLimit | 60 requests per IP per minute, returns 429 on excess |
| Cache | In-memory response cache with per-route TTLs (2–15 min) |

---

## ML Models and Algorithms

### FP-Growth — Market Basket Analysis
- Library: `mlxtend`
- Input: 19,691 order baskets
- Output: Association rules with support, confidence, lift
- Default thresholds: support ≥ 1%, confidence ≥ 20%, lift ≥ 1.0
- Key result: Latte → Croissant at 68.5% confidence, 2.22× lift

### Facebook Prophet — Sales Forecasting
- Library: `prophet`
- Input: 366-day daily revenue time series
- Configuration: Multiplicative seasonality, 13 Mumbai holidays, 90% confidence intervals
- Output: 30-day forward forecast with confidence band
- MAPE on 30-day holdout: ~11–13%

### RoBERTa — Sentiment Analysis
- Model: `cardiffnlp/twitter-roberta-base-sentiment`
- Library: `transformers`
- Input: Customer review text
- Output: Positive / Neutral / Negative classification + compound score
- Strategy: All reviews scored at startup and cached in memory for fast serving

---

## Performance Notes

| Endpoint | First call | Cached call |
|---|---|---|
| `/api/mba/results` | ~2–3 seconds | Instant |
| `/api/forecast/dashboard` | ~4–5 seconds | Instant |
| `/api/kpi/dashboard` | ~100–300ms | Instant |
| `/api/sentiment/dashboard` | ~50ms | Instant |
| `/api/inventory/dashboard` | ~50ms | Instant |

MBA and forecasting endpoints are slow on first call because FP-Growth and Prophet run fresh computations. The cache middleware serves all subsequent calls within the TTL window instantly.

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:pass@localhost:5432/cafe_db` |

For production, also set `SECRET_KEY` in `auth.py` to a strong random string and move it to `.env`.

---

## Known Limitations

- The synthetic dataset covers calendar year 2024. Date filters use `MAX(timestamp)` as anchor rather than the current date, so period filters (7d, 30d, etc.) work correctly with historical data.
- RoBERTa inference runs on CPU — no GPU required but warming 1,292 reviews takes approximately 2 minutes on first startup.
- The in-memory cache resets on every server restart. Prophet retrains and MBA reruns on the first request after each restart.
- Authentication uses a single hardcoded secret key — change `SECRET_KEY` in `auth.py` before any production deployment.

---

## Default Login

| Field | Value |
|---|---|
| Email | `admin@brewanalytics.com` |
| Password | `admin123` |

---

## License

This project was built for academic and portfolio purposes.