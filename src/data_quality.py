#!/usr/bin/env python3
"""
======== data_quality.py ========
Step 9: Data Quality Checks & Monitoring
"""

import psycopg2
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ---- Connect ----
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '5433')),
    database=os.getenv('DB_NAME', 'crypto_db'),
    user=os.getenv('DB_USER', 'crypto_user'),
    password=os.getenv('DB_PASSWORD', 'crypto_pass')
)
print(f"[DQ] Connected to {os.getenv('DB_NAME')} @ {os.getenv('DB_PORT')}")
print(f"[DQ] Timestamp: {datetime.now().isoformat()}")
print("=" * 70)

results = {}
cur = conn.cursor()

# ---- CHECK 1: Row Count by Layer ----
print("\n[CHECK 1] ROW COUNT BY LAYER")
print("-" * 40)

cur.execute("SELECT COUNT(*) FROM bronze.raw_coin_markets")
bronze_rows = cur.fetchone()[0]
print(f"  Bronze: {bronze_rows} rows")
results['bronze_row_count'] = {
    'expected': '>=200', 'actual': bronze_rows,
    'status': 'PASS' if bronze_rows >= 200 else 'FAIL'
}

cur.execute("SELECT COUNT(*) FROM silver.coin_market_data")
silver_rows = cur.fetchone()[0]
print(f"  Silver: {silver_rows} rows")
results['silver_row_count'] = {
    'expected': '>=200', 'actual': silver_rows,
    'status': 'PASS' if silver_rows >= 200 else 'FAIL'
}

gold_tables = ['top_10_coins', 'market_summary', 'top_gainers_losers',
               'volume_analysis', 'market_trends']
print(f"  Gold: {len(gold_tables)} tables")
for table in gold_tables:
    cur.execute(f"SELECT COUNT(*) FROM gold.{table}")
    count = cur.fetchone()[0]
    print(f"    - {table}: {count} rows")
    results[f'gold_{table}_count'] = {
        'expected': '>=1', 'actual': count,
        'status': 'PASS' if count >= 1 else 'FAIL'
    }

# ---- CHECK 2: NULL Rate in Silver ----
print("\n[CHECK 2] NULL RATES IN SILVER")
print("-" * 40)

silver_df = pd.read_sql("""
    SELECT coin_id, symbol, name, rank, price_usd, market_cap, 
           volume_24h, price_change_24h, price_change_pct_24h,
           circulating_supply, total_supply, max_supply
    FROM silver.coin_market_data
""", conn)

total_cells = len(silver_df) * len(silver_df.columns)
null_count = silver_df.isnull().sum().sum()
null_pct = (null_count / total_cells) * 100
print(f"  Total cells: {total_cells}")
print(f"  Null cells: {null_count}")
print(f"  Null rate: {null_pct:.2f}%")
results['null_rate'] = {
    'expected': '<5%', 'actual': f'{null_pct:.2f}%',
    'status': 'PASS' if null_pct < 5 else 'WARN'
}

print("\n  By column:")
for col in silver_df.columns:
    col_nulls = silver_df[col].isnull().sum()
    col_pct = (col_nulls / len(silver_df)) * 100
    status = 'OK' if col_pct < 10 else 'WARN'
    print(f"    {col}: {col_nulls} nulls ({col_pct:.1f}%) [{status}]")
    results[f'null_{col}'] = {
        'count': int(col_nulls), 'pct': f'{col_pct:.1f}%', 'status': status
    }

# ---- CHECK 3: Data Freshness ----
print("\n[CHECK 3] DATA FRESHNESS")
print("-" * 40)

cur.execute("SELECT MAX(processed_at) FROM silver.coin_market_data")
last_processed = cur.fetchone()[0]
print(f"  Last processed: {last_processed}")

now = datetime.now()
age = now - last_processed
print(f"  Data age: {age}")

if age < timedelta(hours=24):
    freshness_status = 'PASS'
    print(f"  Status: FRESH (<24h)")
elif age < timedelta(hours=48):
    freshness_status = 'WARN'
    print(f"  Status: STALE (24-48h)")
else:
    freshness_status = 'FAIL'
    print(f"  Status: EXPIRED (>48h)")

results['data_freshness'] = {
    'age_hours': age.total_seconds() / 3600,
    'status': freshness_status
}

# ---- CHECK 4: Price Anomalies ----
print("\n[CHECK 4] PRICE ANOMALIES")
print("-" * 40)

zero_prices = silver_df[silver_df['price_usd'] <= 0]['coin_id'].tolist()
if zero_prices:
    print(f"  ⚠️  Coins with zero/negative price: {zero_prices}")
    results['price_anomaly'] = {'status': 'FAIL', 'coins': zero_prices}
else:
    print("  ✓  No zero/negative prices found")
    results['price_anomaly'] = {'status': 'PASS'}

extreme_changes = silver_df[
    silver_df['price_change_pct_24h'].abs() > 500
][['coin_id', 'price_change_pct_24h']].to_dict('records')
if extreme_changes:
    print(f"  ⚠️  Extreme price changes (>500%): {len(extreme_changes)} coins")
    print(f"    Top 3: {extreme_changes[:3]}")
    results['extreme_change'] = {'status': 'WARN', 'count': len(extreme_changes)}
else:
    print("  ✓  No extreme price changes")
    results['extreme_change'] = {'status': 'PASS'}

# ---- CHECK 5: Gold Layer Integrity ----
print("\n[CHECK 5] GOLD LAYER INTEGRITY")
print("-" * 40)

cur.execute("SELECT COUNT(*) FROM gold.top_10_coins")
top10_count = cur.fetchone()[0]
print(f"  top_10_coins rows: {top10_count} (expected 10)")
results['gold_top10_count'] = {
    'expected': 10, 'actual': top10_count,
    'status': 'PASS' if top10_count == 10 else 'FAIL'
}

cur.execute("SELECT COUNT(*) FROM gold.market_summary")
summary_count = cur.fetchone()[0]
print(f"  market_summary rows: {summary_count} (expected >=4)")
results['gold_summary_count'] = {
    'expected': '>=4', 'actual': summary_count,
    'status': 'PASS' if summary_count >= 4 else 'FAIL'
}

# ---- CHECK 6: Pipeline Run Log ----
print("\n[CHECK 6] PIPELINE RUN LOG")
print("-" * 40)

log_entry = {
    'timestamp': datetime.now().isoformat(),
    'bronze_rows': bronze_rows,
    'silver_rows': silver_rows,
    'null_rate_pct': round(null_pct, 2),
    'data_freshness': freshness_status,
    'price_anomaly': results['price_anomaly']['status'],
    'summary': {
        'total_checks': len([k for k, v in results.items() if 'status' in str(v)]),
        'passes': len([k for k, v in results.items() if v.get('status') == 'PASS']),
        'warns': len([k for k, v in results.items() if v.get('status') == 'WARN']),
        'fails': len([k for k, v in results.items() if v.get('status') == 'FAIL'])
    }
}

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dq_runs.json')
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        logs = json.load(f)
else:
    logs = []
logs.append(log_entry)
with open(log_file, 'w') as f:
    json.dump(logs, f, indent=2)

print(f"  Run logged to: {log_file}")
print(f"  Total runs logged: {len(logs)}")

# ---- FINAL SUMMARY ----
print("\n" + "=" * 70)
print("[DQ SUMMARY]")
print("=" * 70)
total = len([k for k, v in results.items() if 'status' in str(v)])
passes = len([k for k, v in results.items() if v.get('status') == 'PASS'])
warns = len([k for k, v in results.items() if v.get('status') == 'WARN'])
fails = len([k for k, v in results.items() if v.get('status') == 'FAIL'])

print(f"  Total Checks: {total}")
print(f"  ✅ PASS: {passes}")
print(f"  ⚠️  WARN: {warns}")
print(f"  ❌ FAIL: {fails}")

if fails > 0:
    print("\n  ❌ PIPELINE DATA QUALITY CHECKS FAILED!")
    cur.close()
    conn.close()
    exit(1)
elif warns > 0:
    print("\n  ⚠️  PIPELINE DATA QUALITY CHECKS HAVE WARNINGS")
else:
    print("\n  ✅ ALL DATA QUALITY CHECKS PASSED!")

cur.close()
conn.close()