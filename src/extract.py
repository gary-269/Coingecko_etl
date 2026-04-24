import requests
import pandas as pd
import json
import logging
from datetime import datetime
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoinGeckoExtractor:
    """Extract cryptocurrency data from CoinGecko API"""
    
    def __init__(self):
        self.base_url = Config.COINGECKO_BASE_URL
        self.per_page = Config.PER_PAGE
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json"
        })
    
    def get_markets(self, page=1, per_page=None):
        """Fetch top cryptocurrency markets data"""
        per_page = per_page or self.per_page
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d,30d"
        }
        
        logger.info(f"Fetching page {page} from CoinGecko...")
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched {len(data)} records from page {page}")
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded. Waiting...")
                import time
                time.sleep(60)
                return self.get_markets(page, per_page)
            raise
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            raise
    
    def get_coin_history(self, coin_id, date=None):
        """Fetch historical data for a specific coin"""
        url = f"{self.base_url}/coins/{coin_id}/history"
        params = {"date": date or datetime.now().strftime("%d-%m-%Y")}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching history for {coin_id}: {str(e)}")
            return None
    
    def get_market_chart(self, coin_id, days="30"):
        """Fetch market chart data (price, market cap, volume over time)"""
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching market chart for {coin_id}: {str(e)}")
            return None
    
    def fetch_all_markets(self, max_pages=3):
        """Fetch multiple pages of market data"""
        all_data = []
        for page in range(1, max_pages + 1):
            data = self.get_markets(page=page)
            if not data:
                break
            all_data.extend(data)
            import time
            time.sleep(2)  # Respect rate limits
        return all_data
    
    def fetch_historical_for_top_coins(self, days=7):
        """Fetch historical chart data for top tracked coins"""
        historical_data = {}
        for coin_id in Config.TRACKED_COINS:
            logger.info(f"Fetching market chart for {coin_id}...")
            chart_data = self.get_market_chart(coin_id, days=str(days))
            if chart_data:
                historical_data[coin_id] = chart_data
            import time
            time.sleep(2)
        return historical_data
    
    def extract_to_dataframe(self, data):
        """Convert API response to pandas DataFrame"""
        df = pd.json_normalize(data)
        df['extraction_timestamp'] = datetime.now().isoformat()
        df['source'] = 'coingecko_markets'
        return df


if __name__ == "__main__":
    extractor = CoinGeckoExtractor()
    
    # Fetch markets data
    markets = extractor.fetch_all_markets(max_pages=2)
    df = extractor.extract_to_dataframe(markets)
    print(f"Extracted {len(df)} records")
    print(df.columns.tolist())
    print(df[['id', 'symbol', 'name', 'current_price', 'market_cap']].head())