import os
import psycopg2
import json
import logging
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from src.extract import CoinGeckoExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BronzeLoader:
    """Load raw extracted data into Bronze layer (PostgreSQL)"""
    
    def __init__(self):
        self.extractor = CoinGeckoExtractor()
    
    def get_connection(self):
        return psycopg2.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
    
    def create_bronze_tables(self):
        """Create bronze schema and tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("CREATE SCHEMA IF NOT EXISTS bronze")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze.raw_coin_markets (
                id SERIAL PRIMARY KEY,
                raw_data JSONB NOT NULL,
                extraction_timestamp TIMESTAMP NOT NULL,
                source VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze.raw_coin_history (
                id SERIAL PRIMARY KEY,
                coin_id VARCHAR(100) NOT NULL,
                raw_data JSONB NOT NULL,
                extraction_date DATE NOT NULL,
                extraction_timestamp TIMESTAMP NOT NULL,
                source VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze.raw_market_chart (
                id SERIAL PRIMARY KEY,
                coin_id VARCHAR(100) NOT NULL,
                raw_data JSONB NOT NULL,
                extraction_timestamp TIMESTAMP NOT NULL,
                source VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_markets_ts 
            ON bronze.raw_coin_markets (extraction_timestamp DESC)
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Bronze tables created successfully")
    
    def load_markets(self):
        """Load market data to bronze"""
        data = self.extractor.fetch_all_markets(max_pages=2)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for record in data:
            raw_json = json.dumps(record)
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO bronze.raw_coin_markets (raw_data, extraction_timestamp, source)
                VALUES (%s, %s, %s)
            """, (raw_json, timestamp, "coingecko_markets"))
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Loaded {len(data)} market records to bronze layer")
        return len(data)
    
    def load_coin_history(self):
        """Load historical data for tracked coins"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for coin_id in Config.TRACKED_COINS[:10]:
            history = self.extractor.get_coin_history(coin_id)
            if history:
                raw_json = json.dumps(history)
                timestamp = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO bronze.raw_coin_history 
                    (coin_id, raw_data, extraction_date, extraction_timestamp, source)
                    VALUES (%s, %s, %s, %s, %s)
                """, (coin_id, raw_json, datetime.now().date(), timestamp, "coingecko_history"))
                count += 1
            import time
            time.sleep(2)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Loaded history for {count} coins to bronze layer")
        return count
    
    def load_market_charts(self, days=7):
        """Load market chart data"""
        historical = self.extractor.fetch_historical_for_top_coins(days=days)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for coin_id, chart_data in historical.items():
            if chart_data:
                raw_json = json.dumps(chart_data)
                timestamp = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO bronze.raw_market_chart (coin_id, raw_data, extraction_timestamp, source)
                    VALUES (%s, %s, %s, %s)
                """, (coin_id, raw_json, timestamp, "coingecko_chart"))
                count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Loaded market charts for {count} coins to bronze layer")
        return count


if __name__ == "__main__":
    loader = BronzeLoader()
    loader.create_bronze_tables()
    loader.load_markets()
    loader.load_coin_history()
    loader.load_market_charts(days=7)