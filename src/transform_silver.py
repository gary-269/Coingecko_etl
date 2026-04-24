# ===========================================
# transform_silver.py
# STEP 5: SILVER LAYER - Clean & Transform Bronze Data
# ===========================================

import pandas as pd
import numpy as np
from datetime import datetime
import sys, os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
import psycopg2


# ===========================================
# DATABASE CONNECTION
# ===========================================

def get_db_connection():
    """Connect to PostgreSQL using Config credentials"""
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        print("[INFO] Connected to PostgreSQL")
        return conn
    except Exception as e:
        print(f"[ERROR] DB connection failed: {e}")
        raise


def read_bronze_data(conn):
    """Read all raw data from Bronze layer and extract from JSONB"""
    query = """
        SELECT 
            id,
            raw_data,
            extraction_timestamp,
            source
        FROM bronze.raw_coin_markets 
        ORDER BY extraction_timestamp DESC
        LIMIT 250
    """
    print("[INFO] Reading Bronze data from raw_coin_markets...")
    df = pd.read_sql_query(query, conn)
    print(f"[INFO] Loaded {len(df)} rows from Bronze layer")
    
    # Extract JSON fields into columns
    print("[INFO] Extracting JSON fields...")
    extracted_data = []
    
    for _, row in df.iterrows():
        try:
            raw_json = row['raw_data'] if isinstance(row['raw_data'], dict) else json.loads(row['raw_data'])
            
            # Extract fields from JSON
            extracted_row = {
                'coin_id': raw_json.get('id', 'unknown'),
                'symbol': raw_json.get('symbol', ''),
                'name': raw_json.get('name', ''),
                'rank': raw_json.get('market_cap_rank'),
                'price_usd': raw_json.get('current_price'),
                'market_cap': raw_json.get('market_cap'),
                'volume_24h': raw_json.get('total_volume'),
                'price_change_24h': raw_json.get('price_change_24h'),
                'price_change_pct_24h': raw_json.get('price_change_percentage_24h'),
                'circulating_supply': raw_json.get('circulating_supply'),
                'total_supply': raw_json.get('total_supply'),
                'max_supply': raw_json.get('max_supply'),
                'extraction_timestamp': row['extraction_timestamp']
            }
            extracted_data.append(extracted_row)
        except Exception as e:
            print(f"[WARN] Error extracting row {row['id']}: {e}")
    
    extracted_df = pd.DataFrame(extracted_data)
    print(f"[INFO] Successfully extracted {len(extracted_df)} records")
    return extracted_df

def load_silver_data(conn, df):
    """Create Silver schema, table, and load cleaned data"""
    cursor = conn.cursor()
    
    # Create silver schema if not exists
    cursor.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    cursor.execute("GRANT ALL ON SCHEMA silver TO crypto_user;")
    
    # Create Silver table
    create_sql = """
        CREATE TABLE IF NOT EXISTS silver.coin_market_data (
            id SERIAL PRIMARY KEY,
            coin_id VARCHAR(50) NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            name VARCHAR(100) NOT NULL,
            rank INTEGER,
            price_usd DECIMAL(20,8),
            market_cap DECIMAL(20,2),
            volume_24h DECIMAL(20,2),
            price_change_24h DECIMAL(20,8),
            price_change_pct_24h DECIMAL(10,4),
            circulating_supply DECIMAL(20,8),
            total_supply DECIMAL(20,8),
            max_supply DECIMAL(20,8),
            is_active BOOLEAN DEFAULT TRUE,
            data_quality_score INTEGER DEFAULT 100,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    cursor.execute(create_sql)
    cursor.execute("GRANT ALL ON ALL TABLES IN SCHEMA silver TO crypto_user;")
    print("[INFO] Silver schema and table created/verified")
    
    # Insert data
    insert_sql = """
        INSERT INTO silver.coin_market_data 
        (coin_id, symbol, name, rank, price_usd, market_cap, volume_24h,
         price_change_24h, price_change_pct_24h, circulating_supply,
         total_supply, max_supply, is_active, data_quality_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    rows_loaded = 0
    for _, row in df.iterrows():
        try:
            cursor.execute(insert_sql, (
                row['coin_id'],
                row['symbol'].upper() if pd.notna(row['symbol']) else 'UNK',
                row['name'],
                int(row['rank']) if pd.notna(row['rank']) else None,
                float(row['price_usd']) if pd.notna(row['price_usd']) else None,
                float(row['market_cap']) if pd.notna(row['market_cap']) else None,
                float(row['volume_24h']) if pd.notna(row['volume_24h']) else None,
                float(row['price_change_24h']) if pd.notna(row['price_change_24h']) else None,
                float(row['price_change_pct_24h']) if pd.notna(row['price_change_pct_24h']) else None,
                float(row['circulating_supply']) if pd.notna(row['circulating_supply']) else None,
                float(row['total_supply']) if pd.notna(row['total_supply']) else None,
                float(row['max_supply']) if pd.notna(row['max_supply']) else None,
                True,
                int(row['data_quality_score'])
            ))
            rows_loaded += 1
        except Exception as e:
            print(f"[WARN] Skipping row: {e}")
    
    conn.commit()
    cursor.close()
    print(f"[INFO] Loaded {rows_loaded} rows into silver.coin_market_data")
    return rows_loaded

    


# ===========================================
# STEP 5: CLEAN BRONZE -> SILVER
# ===========================================

def clean_bronze_data(df):
    """
    Step 5: Clean & transform Bronze data into Silver
    """
    print("\n" + "="*50)
    print("[STEP 5] CLEANING BRONZE DATA FOR SILVER LAYER")
    print("="*50)
    
    stats = {
        'original_rows': len(df),
        'nulls_filled': 0,
        'duplicates_removed': 0,
        'invalid_rows_removed': 0
    }
    
    # --- 1. Handle Nulls ---
    print("\n[CLEAN 1] Handling NULL values...")
    
    numeric_cols = [
        'price_usd', 'market_cap', 'volume_24h',
        'price_change_24h', 'price_change_pct_24h',
        'circulating_supply', 'total_supply', 'max_supply'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                df[col] = df[col].fillna(0)
                print(f"  - Filled {null_count} nulls in '{col}'")
                stats['nulls_filled'] += null_count
    
    df['name'] = df['name'].fillna('Unknown')
    df['symbol'] = df['symbol'].fillna('UNK')
    df['coin_id'] = df['coin_id'].fillna('unknown')
    
    # --- 2. Enforce Types ---
    print("\n[CLEAN 2] Enforcing data types...")
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df['rank'] = pd.to_numeric(df['rank'], errors='coerce').fillna(0).astype('int64')
    df['price_usd'] = df['price_usd'].round(8)
    df['price_change_pct_24h'] = df['price_change_pct_24h'].round(4)
    print("  - All numeric types enforced")
    
    # --- 3. Remove Duplicates ---
    print("\n[CLEAN 3] Removing duplicates...")
    
    before = len(df)
    df = df.sort_values('rank', ascending=True).drop_duplicates(
        subset=['coin_id'], keep='first'
    )
    stats['duplicates_removed'] = before - len(df)
    print(f"  - Removed {stats['duplicates_removed']} duplicate coin_ids")
    
    # --- 4. Remove Invalid ---
    print("\n[CLEAN 4] Removing invalid rows...")
    
    before = len(df)
    df = df[df['price_usd'] > 0]  # Only keep rows with positive prices
    stats['invalid_rows_removed'] = before - len(df)
    print(f"  - Removed {stats['invalid_rows_removed']} rows with invalid prices")
    
    # --- 5. Data Quality Score ---
    print("\n[CLEAN 5] Calculating data quality scores...")
    
    def calc_score(row):
        score = 100
        if row.get('market_cap', 0) == 0: score -= 15
        if row.get('volume_24h', 0) == 0: score -= 10
        if row.get('circulating_supply', 0) == 0: score -= 10
        if row.get('rank', 0) == 0: score -= 10
        return max(0, score)
    
    df['data_quality_score'] = df.apply(calc_score, axis=1)
    print(f"  - Quality scores: {df['data_quality_score'].min()} - {df['data_quality_score'].max()}")
    
    # --- 6. Summary ---
    print("\n[CLEAN 6] Cleaning Summary:")
    print(f"  Original rows:      {stats['original_rows']}")
    print(f"  Final rows:         {len(df)}")
    print(f"  Nulls filled:       {stats['nulls_filled']}")
    print(f"  Duplicates removed: {stats['duplicates_removed']}")
    print(f"  Invalid rows:       {stats['invalid_rows_removed']}")
    if len(df) > 0:
        print(f"  Avg quality score:  {df['data_quality_score'].mean():.1f}/100")
    
    return df, stats


# ===========================================
# MAIN PIPELINE
# ===========================================

def main():
    """Main pipeline: Bronze -> Silver transformation"""
    print("\n" + "#"*60)
    print("#  SILVER LAYER PIPELINE")
    print("#"*60)
    print(f"  DB: {Config.DB_NAME} @ {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"  Bronze schema: {Config.BRONZE_SCHEMA}")
    print(f"  Silver schema: {Config.SILVER_SCHEMA}")
    print("#"*60)
    
    conn = None
    try:
        conn = get_db_connection()
        
        bronze_df = read_bronze_data(conn)
        if bronze_df.empty:
            print("[ERROR] Bronze layer is empty!")
            return
        
        silver_df, stats = clean_bronze_data(bronze_df)
        
        if not silver_df.empty:
            rows_loaded = load_silver_data(conn, silver_df)
        else:
            print("[ERROR] No data to load after cleaning!")
            return
        
        print("\n" + "="*50)
        print("[SUCCESS] Silver transformation complete!")
        print(f"  Bronze rows:  {stats['original_rows']}")
        print(f"  Silver rows:  {len(silver_df)}")
        print(f"  Rows loaded:  {rows_loaded}")
        print("="*50)
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("\n[INFO] Connection closed")


if __name__ == "__main__":
    main()