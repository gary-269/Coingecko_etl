-- Bronze Schema (Raw Data Layer)
CREATE SCHEMA IF NOT EXISTS bronze;

-- Raw coin markets - stores full JSON API response
CREATE TABLE IF NOT EXISTS bronze.raw_coin_markets (
    id SERIAL PRIMARY KEY,
    raw_data JSONB NOT NULL,
    extraction_timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw coin history
CREATE TABLE IF NOT EXISTS bronze.raw_coin_history (
    id SERIAL PRIMARY KEY,
    coin_id VARCHAR(100) NOT NULL,
    raw_data JSONB NOT NULL,
    extraction_date DATE NOT NULL,
    extraction_timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw market chart data
CREATE TABLE IF NOT EXISTS bronze.raw_market_chart (
    id SERIAL PRIMARY KEY,
    coin_id VARCHAR(100) NOT NULL,
    raw_data JSONB NOT NULL,
    extraction_timestamp TIMESTAMP NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_raw_markets_ts 
    ON bronze.raw_coin_markets (extraction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_raw_history_coin 
    ON bronze.raw_coin_history (coin_id, extraction_date DESC);