import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "crypto_db")
    DB_USER = os.getenv("DB_USER", "crypto_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "crypto_pass")
    
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # CoinGecko API
    COINGECKO_BASE_URL = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3")
    PER_PAGE = int(os.getenv("COINGECKO_PER_PAGE", "100"))
    
    # Schemas
    BRONZE_SCHEMA = "bronze"
    SILVER_SCHEMA = "silver"
    GOLD_SCHEMA = "gold"
    
    # Supported coins to track (top 20)
    TRACKED_COINS = [
        "bitcoin", "ethereum", "tether", "binancecoin", "ripple",
        "usd-coin", "solana", "cardano", "dogecoin", "tron",
        "avalanche-2", "shiba-inu", "polkadot", "chainlink", "polygon",
        "bitcoin-cash", "near", "uniswap", "litecoin", "internet-computer"
    ]