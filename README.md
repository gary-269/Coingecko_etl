
---

## ▶️ 9-Step Pipeline

| Step | Description | File |
|------|-------------|------|
| 1 | **API Selection** — CoinGecko (real, messy, no API key) | — |
| 2 | **Data Extraction** — Fetch top 250 coins by market cap | `src/extract.py` |
| 3 | **Schema Design** — Bronze/Silver/Gold medallion in Postgres | — |
| 4 | **Bronze Layer** — Raw JSON stored as `jsonb` | `src/load_bronze.py` |
| 5 | **Silver Layer** — Cleaned, typed (`DECIMAL(30,12)`) | `src/create_silver.py` |
| 6 | **Gold Layer** — 5 aggregation tables with KPIs | `src/build_gold.py` |
| 7 | **BI Dashboard** — Streamlit interactive visualization | `src/dashboard.py` |
| 8 | **Orchestration** — Prefect daily 8 AM EDT schedule | `src/pipeline_flow.py` |
| 9 | **Data Quality** — 6 DQ checks with run logging | `src/data_quality.py` |

---

## 📦 Gold Layer Tables

| Table | Description | Rows |
|-------|-------------|------|
| `top_10_coins` | Largest coins by market cap | 10 |
| `market_summary` | Aggregate market metrics (avg price, total market cap, etc.) | 4 |
| `top_gainers_losers` | Top 10 gainers + top 10 losers (24h) | 20 |
| `volume_analysis` | Top 20 by volume + vol-to-market-cap ratio | 20 |
| `market_trends` | Market sentiment + volatility level | 2 |

---

## 🛠️ Tech Stack

- **Language:** Python 3.13
- **Database:** PostgreSQL (Docker, port 5433)
- **API:** CoinGecko Markets API
- **Libraries:** `psycopg2`, `pandas`, `requests`, `python-dotenv`
- **Orchestration:** Prefect (daily cron)
- **BI:** Streamlit
- **Containerization:** Docker Compose

---

## 🚀 Quick Start

### Prerequisites

```bash
git clone https://github.com/YOUR_USERNAME/Coingecko_etl.git
cd Coingecko_etl

python -m venv etlenv
source etlenv/bin/activate
pip install -r requirements.txt

docker-compose up -d
```

### Configure `.env`

```env
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=crypto_db
DB_USER=crypto_user
DB_PASSWORD=crypto_pass
```

### Run Full Pipeline

```bash
python src/extract.py          # Step 2
python src/load_bronze.py      # Step 4
python src/create_silver.py    # Step 5
python src/build_gold.py       # Step 6
python src/data_quality.py     # Step 9
```

---

## 📊 Dashboard

```bash
streamlit run src/dashboard.py
```

Open [http://localhost:8501](http://localhost:8501) — KPI cards, top coins, gainers/losers, volume analysis.

---

## ⏰ Orchestration

Daily at 8 AM Eastern Time:

```bash
# Terminal 1
source etlenv/bin/activate
prefect server start

# Terminal 2
source etlenv/bin/activate
prefect worker start --pool default-worker-pool -t process
```

View at [http://localhost:4200](http://localhost:4200).

---

## ✅ Data Quality Checks

```bash
python src/data_quality.py
```

| Check | Description | Threshold |
|-------|-------------|-----------|
| **Row Count** | Bronze ≥200, Silver ≥200, Gold ≥1 each | Row counts |
| **Null Rate** | Scan Silver columns | <5% overall |
| **Data Freshness** | Last processed <24h ago | <24h |
| **Price Anomalies** | Zero prices, >500% changes | None |
| **Gold Integrity** | top_10_coins = 10, market_summary ≥4 | Exact |
| **Run Logging** | Append to `dq_runs.json` | Always |

---

## 🔍 Key Design Decisions

- **DECIMAL(30,12)** — Handles Bitcoin's $1T+ market cap without overflow
- **ON CONFLICT DO NOTHING** — Prevents duplicates from aborting transactions
- **`jsonb` in Bronze** — Preserves raw API response for reprocessing
- **`float()` conversion** — Ensures psycopg2 compatibility with pandas types
- **Port 5433** — Avoids conflict with local Postgres (5432)
- **Docker Compose** — Reproducible environment

---

## 👤 Author

**Karanveer Singh** — Data Engineer

End-to-end ETL pipeline with production considerations: orchestration, data quality monitoring, and interactive visualization.

---

## 📄 License

MIT License