# ===========================================
# build_gold.py
# STEP 6: GOLD LAYER - Business-Ready Datasets
# ===========================================

import pandas as pd
import numpy as np
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
import psycopg2


# ===========================================
# DATABASE CONNECTION
# ===========================================

def get_db_connection():
    """Connect to PostgreSQL"""
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


def read_silver_data(conn):
    """Read all cleaned data from Silver layer"""
    query = """
        SELECT coin_id, symbol, name, rank, price_usd, market_cap, 
               volume_24h, price_change_24h, price_change_pct_24h,
               circulating_supply, total_supply, max_supply,
               data_quality_score, processed_at
        FROM silver.coin_market_data 
        ORDER BY processed_at DESC
    """
    print("[INFO] Reading Silver data...")
    df = pd.read_sql_query(query, conn)
    print(f"[INFO] Loaded {len(df)} rows from Silver layer")
    return df


# ===========================================
# GOLD TABLE 1: TOP_10_COINS
# ===========================================

def build_top_10_coins(conn, df):
    """Build top 10 coins by market cap"""
    print("\n[GOLD 1] Building TOP_10_COINS...")
    cursor = conn.cursor()
    
    cursor.execute("CREATE SCHEMA IF NOT EXISTS gold;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold.top_10_coins (
            id SERIAL PRIMARY KEY,
            coin_id VARCHAR(50) NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            name VARCHAR(100) NOT NULL,
            rank INTEGER NOT NULL,
            market_cap DECIMAL(20,2) NOT NULL,
            price_usd DECIMAL(20,8) NOT NULL,
            volume_24h DECIMAL(20,2),
            price_change_pct_24h DECIMAL(10,4),
            data_quality_score INTEGER,
            snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    top_10 = df.nlargest(10, 'market_cap')[
        ['coin_id', 'symbol', 'name', 'rank', 'market_cap', 
         'price_usd', 'volume_24h', 'price_change_pct_24h', 'data_quality_score']
    ]
    
    insert_sql = """
        INSERT INTO gold.top_10_coins 
        (coin_id, symbol, name, rank, market_cap, price_usd, 
         volume_24h, price_change_pct_24h, data_quality_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    rows_loaded = 0
    for _, row in top_10.iterrows():
        cursor.execute(insert_sql, (
            row['coin_id'], row['symbol'], row['name'], row['rank'],
            row['market_cap'], row['price_usd'], row['volume_24h'],
            row['price_change_pct_24h'], row['data_quality_score']
        ))
        rows_loaded += 1
    
    conn.commit()
    cursor.close()
    print(f"  - Loaded {rows_loaded} rows into gold.top_10_coins")
    return top_10


# ===========================================
# GOLD TABLE 2: MARKET_SUMMARY
# ===========================================

def build_market_summary(conn, df):
    """Build market summary statistics"""
    print("\n[GOLD 2] Building MARKET_SUMMARY...")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold.market_summary (
            id SERIAL PRIMARY KEY,
            total_market_cap DECIMAL(20,2),
            avg_price DECIMAL(20,8),
            median_price DECIMAL(20,8),
            max_price DECIMAL(20,8),
            min_price DECIMAL(20,8),
            total_volume_24h DECIMAL(20,2),
            avg_price_change_pct DECIMAL(10,4),
            coins_up DECIMAL(10,2),
            coins_down DECIMAL(10,2),
            total_coins INTEGER,
            avg_quality_score DECIMAL(10,2),
            summary_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    summary = {
        'total_market_cap': df['market_cap'].sum(),
        'avg_price': df['price_usd'].mean(),
        'median_price': df['price_usd'].median(),
        'max_price': df['price_usd'].max(),
        'min_price': df['price_usd'].min(),
        'total_volume_24h': df['volume_24h'].sum(),
        'avg_price_change_pct': df['price_change_pct_24h'].mean(),
        'coins_up': len(df[df['price_change_pct_24h'] > 0]),
        'coins_down': len(df[df['price_change_pct_24h'] < 0]),
        'total_coins': len(df),
        'avg_quality_score': df['data_quality_score'].mean()
    }
    
    cursor.execute("""
        INSERT INTO gold.market_summary 
        (total_market_cap, avg_price, median_price, max_price, min_price,
         total_volume_24h, avg_price_change_pct, coins_up, coins_down,
         total_coins, avg_quality_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        summary['total_market_cap'], summary['avg_price'], summary['median_price'],
        summary['max_price'], summary['min_price'], summary['total_volume_24h'],
        summary['avg_price_change_pct'], summary['coins_up'], summary['coins_down'],
        summary['total_coins'], summary['avg_quality_score']
    ))
    
    conn.commit()
    cursor.close()
    print(f"  - Total market cap: ${summary['total_market_cap']:,.2f}")
    print(f"  - Coins up: {summary['coins_up']} | Down: {summary['coins_down']}")
    print(f"  - Avg quality score: {summary['avg_quality_score']:.1f}/100")
    return summary


# ===========================================
# GOLD TABLE 3: TOP_GAINERS_LOSERS
# ===========================================

def build_top_gainers_losers(conn, df):
    """Build top 10 gainers and losers"""
    print("\n[GOLD 3] Building TOP_GAINERS_LOSERS...")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold.top_gainers_losers (
            id SERIAL PRIMARY KEY,
            coin_id VARCHAR(50) NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            name VARCHAR(100) NOT NULL,
            price_usd DECIMAL(20,8) NOT NULL,
            price_change_pct_24h DECIMAL(10,4) NOT NULL,
            category VARCHAR(20) NOT NULL,
            category_rank INTEGER NOT NULL,
            snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    top_gainers = df.nlargest(10, 'price_change_pct_24h')[
        ['coin_id', 'symbol', 'name', 'price_usd', 'price_change_pct_24h']
    ].copy()
    top_gainers['category'] = 'gainer'
    top_gainers['category_rank'] = range(1, 11)
    
    top_losers = df.nsmallest(10, 'price_change_pct_24h')[
        ['coin_id', 'symbol', 'name', 'price_usd', 'price_change_pct_24h']
    ].copy()
    top_losers['category'] = 'loser'
    top_losers['category_rank'] = range(1, 11)
    
    movers = pd.concat([top_gainers, top_losers])
    
    insert_sql = """
        INSERT INTO gold.top_gainers_losers 
        (coin_id, symbol, name, price_usd, price_change_pct_24h, category, category_rank)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    rows_loaded = 0
    for _, row in movers.iterrows():
        cursor.execute(insert_sql, (
            row['coin_id'], row['symbol'], row['name'],
            row['price_usd'], row['price_change_pct_24h'],
            row['category'], row['category_rank']
        ))
        rows_loaded += 1
    
    conn.commit()
    cursor.close()
    print(f"  - Top gainer: {top_gainers.iloc[0]['symbol']} (+{top_gainers.iloc[0]['price_change_pct_24h']:.2f}%)")
    print(f"  - Top loser: {top_losers.iloc[0]['symbol']} ({top_losers.iloc[0]['price_change_pct_24h']:.2f}%)")
    print(f"  - Loaded {rows_loaded} rows into gold.top_gainers_losers")
    return movers


# ===========================================
# GOLD TABLE 4: VOLUME_ANALYSIS
# ===========================================

def build_volume_analysis(conn, df):
    """Build volume analysis"""
    print("\n[GOLD 4] Building VOLUME_ANALYSIS...")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold.volume_analysis (
            id SERIAL PRIMARY KEY,
            coin_id VARCHAR(50) NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            name VARCHAR(100) NOT NULL,
            volume_24h DECIMAL(20,2) NOT NULL,
            volume_to_market_cap_ratio DECIMAL(10,6),
            volume_rank INTEGER,
            snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    volume_analysis = df[
        ['coin_id', 'symbol', 'name', 'volume_24h', 'market_cap']
    ].copy()
    
    volume_analysis['volume_to_market_cap_ratio'] = (
        volume_analysis['volume_24h'] / volume_analysis['market_cap'].replace(0, np.nan)
    ).fillna(0)
    
    volume_analysis['volume_rank'] = volume_analysis['volume_24h'].rank(
        ascending=False, method='min'
    ).astype(int)
    
    volume_analysis = volume_analysis.nlargest(50, 'volume_24h')
    
    insert_sql = """
        INSERT INTO gold.volume_analysis 
        (coin_id, symbol, name, volume_24h, volume_to_market_cap_ratio, volume_rank)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    rows_loaded = 0
    for _, row in volume_analysis.iterrows():
        cursor.execute(insert_sql, (
            row['coin_id'], row['symbol'], row['name'],
            row['volume_24h'], row['volume_to_market_cap_ratio'], row['volume_rank']
        ))
        rows_loaded += 1
    
    conn.commit()
    cursor.close()
    print(f"  - Highest volume: {volume_analysis.iloc[0]['symbol']}")
    print(f"  - Loaded {rows_loaded} rows into gold.volume_analysis")
    return volume_analysis


# ===========================================
# GOLD TABLE 5: MARKET_TRENDS
# ===========================================

def build_market_trends(conn, df):
    """Build market trend indicators"""
    print("\n[GOLD 5] Building MARKET_TRENDS...")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold.market_trends (
            id SERIAL PRIMARY KEY,
            trend_type VARCHAR(50) NOT NULL,
            trend_value VARCHAR(100) NOT NULL,
            numeric_value DECIMAL(20,8),
            insight TEXT,
            trend_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    trends = []
    
    bullish_pct = (df['price_change_pct_24h'] > 0).sum() / len(df) * 100
    if bullish_pct > 60:
        trends.append(('market_sentiment', 'BULLISH', bullish_pct, f'{bullish_pct:.1f}% of coins are up'))
    elif bullish_pct < 40:
        trends.append(('market_sentiment', 'BEARISH', bullish_pct, f'{100-bullish_pct:.1f}% of coins are down'))
    else:
        trends.append(('market_sentiment', 'NEUTRAL', bullish_pct, f'Mixed market: {bullish_pct:.1f}% up'))
    
    volatility = df['price_change_pct_24h'].std()
    vol_trend = 'HIGH' if volatility > 10 else 'MODERATE' if volatility > 5 else 'LOW'
    trends.append(('volatility_level', vol_trend, volatility, f'Volatility is {vol_trend.lower()}'))
    
    top_vol = df.loc[df['volume_24h'].idxmax()]
    trends.append(('highest_volume_coin', top_vol['symbol'], top_vol['volume_24h'], f"{top_vol['symbol']} leads volume"))
    
    top_3_mcap = df.nlargest(3, 'market_cap')['market_cap'].sum()
    total_mcap = df['market_cap'].sum()
    concentration = top_3_mcap / total_mcap * 100
    trends.append(('market_concentration', 'TOP_3', concentration, f'Top 3 control {concentration:.1f}% of market'))
    
    insert_sql = """
        INSERT INTO gold.market_trends 
        (trend_type, trend_value, numeric_value, insight)
        VALUES (%s, %s, %s, %s)
    """
    
    rows_loaded = 0
    for trend_type, trend_value, numeric_value, insight in trends:
        cursor.execute(insert_sql, (trend_type, trend_value, numeric_value, insight))
        rows_loaded += 1
        print(f"  - {trend_type}: {trend_value}")
    
    conn.commit()
    cursor.close()
    print(f"  - Loaded {rows_loaded} trend records into gold.market_trends")
    return trends


# ===========================================
# MAIN PIPELINE
# ===========================================

def main():
    """Main pipeline: Silver -> Gold transformation"""
    print("\n" + "#"*60)
    print("#  GOLD LAYER PIPELINE")
    print("#"*60)
    print(f"  DB: {Config.DB_NAME} @ {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"  Gold schema: {Config.GOLD_SCHEMA}")
    print("#"*60)
    
    conn = None
    try:
        conn = get_db_connection()
        
        silver_df = read_silver_data(conn)
        if silver_df.empty:
            print("[ERROR] Silver layer is empty!")
            return
        
        build_top_10_coins(conn, silver_df)
        build_market_summary(conn, silver_df)
        build_top_gainers_losers(conn, silver_df)
        build_volume_analysis(conn, silver_df)
        build_market_trends(conn, silver_df)
        
        print("\n" + "="*50)
        print("[SUCCESS] Gold layer built successfully!")
        print("  Gold tables created:")
        print("    1. gold.top_10_coins")
        print("    2. gold.market_summary")
        print("    3. gold.top_gainers_losers")
        print("    4. gold.volume_analysis")
        print("    5. gold.market_trends")
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