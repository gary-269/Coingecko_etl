# ===========================================
# create_silver.py
# STEP 5: Bronze -> Silver
# ===========================================

import psycopg2
import json
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "5433")),
    database=os.getenv("DB_NAME", "crypto_db"),
    user=os.getenv("DB_USER", "crypto_user"),
    password=os.getenv("DB_PASSWORD", "crypto_pass")
)
print(f"[INFO] Connected to {os.getenv('DB_NAME')} @ {os.getenv('DB_PORT')}")
conn.autocommit = True
cur = conn.cursor()

cur.execute("CREATE SCHEMA IF NOT EXISTS silver;")
cur.execute("""
    CREATE TABLE IF NOT EXISTS silver.coin_market_data (
        id SERIAL PRIMARY KEY,
        coin_id VARCHAR(255) NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        name VARCHAR(100) NOT NULL,
        rank INTEGER,
        price_usd DECIMAL(30,12),
        market_cap DECIMAL(30,2),
        volume_24h DECIMAL(30,2),
        price_change_24h DECIMAL(30,8),
        price_change_pct_24h DECIMAL(15,4),
        circulating_supply DECIMAL(30,8),
        total_supply DECIMAL(30,8),
        max_supply DECIMAL(30,8),
        is_active BOOLEAN DEFAULT TRUE,
        data_quality_score INTEGER DEFAULT 100,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(coin_id, processed_at)
    )
""")
print("[STEP 5] Silver table created")

conn.autocommit = False
cur.execute("""
    SELECT id, raw_data FROM bronze.raw_coin_markets 
    ORDER BY extraction_timestamp DESC LIMIT 250
""")
bronze_rows = cur.fetchall()
print(f"[STEP 5] Read {len(bronze_rows)} records from Bronze")

# Use ON CONFLICT so duplicates are skipped without error
insert_sql = """INSERT INTO silver.coin_market_data 
    (coin_id, symbol, name, rank, price_usd, market_cap, volume_24h,
     price_change_24h, price_change_pct_24h, circulating_supply,
     total_supply, max_supply, is_active, data_quality_score)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (coin_id, processed_at) DO NOTHING"""

loaded = 0
for row_id, raw_json in bronze_rows:
    try:
        data = raw_json if isinstance(raw_json, dict) else json.loads(raw_json)
        cur.execute(insert_sql, (
            str(data.get('id', f'unknown_{row_id}')),
            str(data.get('symbol', 'UNK')).upper(),
            str(data.get('name', 'Unknown')),
            int(data.get('market_cap_rank')) if data.get('market_cap_rank') else None,
            float(data.get('current_price')) if data.get('current_price') else None,
            float(data.get('market_cap')) if data.get('market_cap') else None,
            float(data.get('total_volume')) if data.get('total_volume') else None,
            float(data.get('price_change_24h')) if data.get('price_change_24h') else None,
            float(data.get('price_change_percentage_24h')) if data.get('price_change_percentage_24h') else None,
            float(data.get('circulating_supply')) if data.get('circulating_supply') else None,
            float(data.get('total_supply')) if data.get('total_supply') else None,
            float(data.get('max_supply')) if data.get('max_supply') else None,
            True, 100
        ))
        loaded += 1
    except Exception as e:
        conn.rollback()
        print(f"[WARN] Skip row {row_id}: {e}")

conn.commit()
print(f"[INFO] Loaded {loaded} rows into silver.coin_market_data")

cur.execute("SELECT COUNT(*) FROM silver.coin_market_data")
count = cur.fetchone()[0]
print(f"[DEBUG] Silver table has {count} rows")

cur.close()
conn.close()