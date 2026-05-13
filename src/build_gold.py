#!/usr/bin/env python3
"""
======== build_gold.py ========
GOLD LAYER – Aggregations & Insights from Silver
"""

import psycopg2
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv

# ---- Load environment ----
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# ---- Connect ----
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '5433')),
    database=os.getenv('DB_NAME', 'crypto_db'),
    user=os.getenv('DB_USER', 'crypto_user'),
    password=os.getenv('DB_PASSWORD', 'crypto_pass')
)
print(f"[INFO] Connected to {os.getenv('DB_NAME')} @ {os.getenv('DB_PORT')}")

cur = conn.cursor()

# ---- Create Gold schema & tables ----
print("[STEP 1] Creating Gold schema and tables...")
cur.execute("CREATE SCHEMA IF NOT EXISTS gold")

# Table 1: top_10_coins
cur.execute("""
    CREATE TABLE IF NOT EXISTS gold.top_10_coins (
        id SERIAL PRIMARY KEY,
        rank INTEGER,
        coin_id VARCHAR(100),
        symbol VARCHAR(20),
        name VARCHAR(200),
        price_usd DECIMAL(30,12),
        market_cap DECIMAL(30,2),
        volume_24h DECIMAL(30,2),
        price_change_pct_24h DECIMAL(15,4),
        circulating_supply DECIMAL(30,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Table 2: market_summary
cur.execute("""
    CREATE TABLE IF NOT EXISTS gold.market_summary (
        id SERIAL PRIMARY KEY,
        metric_name VARCHAR(50),
        metric_value VARCHAR(100),
        numeric_value DECIMAL(30,8),
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Table 3: top_gainers_losers
cur.execute("""
    CREATE TABLE IF NOT EXISTS gold.top_gainers_losers (
        id SERIAL PRIMARY KEY,
        coin_id VARCHAR(100),
        symbol VARCHAR(20),
        name VARCHAR(200),
        price_change_pct_24h DECIMAL(15,4),
        trend VARCHAR(10),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Table 4: volume_analysis
cur.execute("""
    CREATE TABLE IF NOT EXISTS gold.volume_analysis (
        id SERIAL PRIMARY KEY,
        coin_id VARCHAR(100),
        symbol VARCHAR(20),
        name VARCHAR(200),
        volume_24h DECIMAL(30,2),
        market_cap DECIMAL(30,2),
        vol_to_mcap_ratio DECIMAL(15,6),
        volume_category VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Table 5: market_trends
cur.execute("""
    CREATE TABLE IF NOT EXISTS gold.market_trends (
        id SERIAL PRIMARY KEY,
        trend_type VARCHAR(50),
        trend_value VARCHAR(100),
        numeric_value DECIMAL(15,4),
        insight TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
print("[STEP 1] Gold tables created")

# ---- Read Silver data ----
print("[STEP 2] Reading Silver data...")
cur.execute("""
    SELECT coin_id, symbol, name, rank, price_usd, market_cap, volume_24h,
           price_change_24h, price_change_pct_24h, circulating_supply,
           total_supply, max_supply, data_quality_score
    FROM silver.coin_market_data
""")
columns = [desc[0] for desc in cur.description]
rows = cur.fetchall()
silver_df = pd.DataFrame(rows, columns=columns)
print(f"[INFO] Read {len(silver_df)} rows from Silver")

# ---- CRITICAL FIX: Convert all numeric columns ----
# This fixes the "market_cap has dtype object" error
numeric_cols = ['rank', 'price_usd', 'market_cap', 'volume_24h',
                'price_change_24h', 'price_change_pct_24h',
                'circulating_supply', 'total_supply',
                'max_supply', 'data_quality_score']
for col in numeric_cols:
    if col in silver_df.columns:
        silver_df[col] = pd.to_numeric(silver_df[col], errors='coerce')
print(f"[INFO] Numeric columns converted: {silver_df[numeric_cols].dtypes.to_dict()}")

# ---- Build Gold Tables ----
gold_cur = conn.cursor()

# -- Gold 1: top_10_coins --
print("[GOLD 1] Building top_10_coins...")
top10 = silver_df.nlargest(10, 'market_cap')
for _, row in top10.iterrows():
    gold_cur.execute("""
        INSERT INTO gold.top_10_coins
        (rank, coin_id, symbol, name, price_usd, market_cap, volume_24h,
         price_change_pct_24h, circulating_supply)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        int(row['rank']) if pd.notna(row['rank']) else None,
        row['coin_id'], row['symbol'], row['name'],
        float(row['price_usd']) if pd.notna(row['price_usd']) else None,
        float(row['market_cap']) if pd.notna(row['market_cap']) else None,
        float(row['volume_24h']) if pd.notna(row['volume_24h']) else None,
        float(row['price_change_pct_24h']) if pd.notna(row['price_change_pct_24h']) else None,
        float(row['circulating_supply']) if pd.notna(row['circulating_supply']) else None
    ))
print(f"  → Inserted {len(top10)} rows")

# -- Gold 2: market_summary --
print("[GOLD 2] Building market_summary...")
avg_price = silver_df['price_usd'].mean()
total_market_cap = silver_df['market_cap'].sum()
total_volume = silver_df['volume_24h'].sum()
avg_quality = silver_df['data_quality_score'].mean()
gold_cur.execute("""
    INSERT INTO gold.market_summary
    (metric_name, metric_value, numeric_value)
    VALUES
    (%s, %s, %s),
    (%s, %s, %s),
    (%s, %s, %s),
    (%s, %s, %s)
""", (
    'avg_price_usd', f'{avg_price:,.2f}', float(avg_price) if pd.notna(avg_price) else 0,
    'total_market_cap', f'{total_market_cap:,.2f}', float(total_market_cap) if pd.notna(total_market_cap) else 0,
    'total_volume_24h', f'{total_volume:,.2f}', float(total_volume) if pd.notna(total_volume) else 0,
    'avg_quality_score', f'{avg_quality:.2f}', float(avg_quality) if pd.notna(avg_quality) else 0
))
print("  → 4 metrics inserted")

# -- Gold 3: top_gainers_losers --
print("[GOLD 3] Building top_gainers_losers...")
gainers = silver_df.nlargest(10, 'price_change_pct_24h')
losers = silver_df.nsmallest(10, 'price_change_pct_24h')

for _, row in gainers.iterrows():
    gold_cur.execute("""
        INSERT INTO gold.top_gainers_losers
        (coin_id, symbol, name, price_change_pct_24h, trend)
        VALUES (%s, %s, %s, %s, %s)
    """, (row['coin_id'], row['symbol'], row['name'],
          float(row['price_change_pct_24h']) if pd.notna(row['price_change_pct_24h']) else 0,
          'GAINER'))

for _, row in losers.iterrows():
    gold_cur.execute("""
        INSERT INTO gold.top_gainers_losers
        (coin_id, symbol, name, price_change_pct_24h, trend)
        VALUES (%s, %s, %s, %s, %s)
    """, (row['coin_id'], row['symbol'], row['name'],
          float(row['price_change_pct_24h']) if pd.notna(row['price_change_pct_24h']) else 0,
          'LOSER'))
print("  → 20 rows inserted (10 gainers, 10 losers)")

# -- Gold 4: volume_analysis --
print("[GOLD 4] Building volume_analysis...")
vol_df = silver_df.dropna(subset=['volume_24h', 'market_cap']).copy()
vol_df['vol_to_mcap_ratio'] = vol_df['volume_24h'] / vol_df['market_cap'].replace(0, pd.NA)
vol_df['volume_category'] = vol_df['vol_to_mcap_ratio'].apply(
    lambda x: 'HIGH' if pd.notna(x) and x > 0.1 else
              'MEDIUM' if pd.notna(x) and x > 0.02 else
              'LOW' if pd.notna(x) else 'UNKNOWN'
)
vol_df = vol_df.nlargest(20, 'volume_24h')

for _, row in vol_df.iterrows():
    gold_cur.execute("""
        INSERT INTO gold.volume_analysis
        (coin_id, symbol, name, volume_24h, market_cap, vol_to_mcap_ratio, volume_category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        row['coin_id'], row['symbol'], row['name'],
        float(row['volume_24h']) if pd.notna(row['volume_24h']) else None,
        float(row['market_cap']) if pd.notna(row['market_cap']) else None,
        float(row['vol_to_mcap_ratio']) if pd.notna(row['vol_to_mcap_ratio']) else None,
        row['volume_category']
    ))
print(f"  → {len(vol_df)} rows inserted")

# -- Gold 5: market_trends --
print("[GOLD 5] Building market_trends...")
bullish_pct = (silver_df['price_change_pct_24h'] > 0).sum() / len(silver_df) * 100
sentiment = 'BULLISH' if bullish_pct > 60 else 'BEARISH' if bullish_pct < 40 else 'NEUTRAL'
gold_cur.execute("""
    INSERT INTO gold.market_trends
    (trend_type, trend_value, numeric_value, insight)
    VALUES (%s, %s, %s, %s)
""", ('market_sentiment', sentiment, float(bullish_pct), f'{bullish_pct:.1f}% of coins are up'))

volatility = silver_df['price_change_pct_24h'].std()
vol_trend = 'HIGH' if pd.notna(volatility) and volatility > 10 else \
            'MODERATE' if pd.notna(volatility) and volatility > 5 else 'LOW'
gold_cur.execute("""
    INSERT INTO gold.market_trends
    (trend_type, trend_value, numeric_value, insight)
    VALUES (%s, %s, %s, %s)
""", ('volatility_level', vol_trend, float(volatility) if pd.notna(volatility) else 0.0,
      f'Volatility is {vol_trend.lower()}'))

print("  → 2 trend records inserted")

# ---- Commit & cleanup ----
conn.commit()
print("\n" + "="*60)
print("[SUCCESS] Gold layer complete!")
print("="*60)
print("  Gold tables created:")
print("    - top_10_coins (10 rows)")
print("    - market_summary (4 rows)")
print("    - top_gainers_losers (20 rows)")
print("    - volume_analysis (20 rows)")
print("    - market_trends (2 rows)")
print(f"\n  Data timestamp: {datetime.now().isoformat()}")

gold_cur.close()
cur.close()
conn.close()