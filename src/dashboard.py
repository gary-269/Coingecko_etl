#!/usr/bin/env python3
"""
======== dashboard.py ========
Streamlit BI Dashboard for CoinGecko Gold Layer
Step 7: BI / Visualization
"""

import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

# ---- Load environment ----
load_dotenv()

st.set_page_config(
    page_title="Crypto Market Dashboard",
    page_icon="📈",
    layout="wide"
)

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '5433')),
        database=os.getenv('DB_NAME', 'crypto_db'),
        user=os.getenv('DB_USER', 'crypto_user'),
        password=os.getenv('DB_PASSWORD', 'crypto_pass')
    )

def load_query(sql):
    conn = get_connection()
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

# ---- Title ----
st.title("📈 Crypto Market Dashboard")
st.markdown("---")

# ---- Sidebar: KPIs from Market Summary ----
try:
    summary_df = load_query("SELECT * FROM gold.market_summary")

    col1, col2, col3, col4 = st.columns(4)

    total_market_cap = summary_df[summary_df['metric_name'] == 'total_market_cap']['numeric_value'].values[0]
    avg_price = summary_df[summary_df['metric_name'] == 'avg_price_usd']['numeric_value'].values[0]
    total_volume = summary_df[summary_df['metric_name'] == 'total_volume_24h']['numeric_value'].values[0]
    avg_quality = summary_df[summary_df['metric_name'] == 'avg_quality_score']['numeric_value'].values[0]

    col1.metric("Total Market Cap", f"${total_market_cap:,.0f}", delta_color="normal")
    col2.metric("Total 24h Volume", f"${total_volume:,.0f}", delta_color="normal")
    col3.metric("Avg Price (USD)", f"${avg_price:,.2f}", delta_color="normal")
    col4.metric("Avg Quality Score", f"{avg_quality:.1f}", delta_color="normal")
except Exception as e:
    st.error(f"Failed to load market summary: {e}")

st.markdown("---")

# ---- Two-column layout ----
left_col, right_col = st.columns(2)

# ---- Left: Top 10 Coins by Market Cap ----
with left_col:
    st.subheader("🏆 Top 10 Coins by Market Cap")
    try:
        top10 = load_query("""
            SELECT coin_id, symbol, name, rank, price_usd, market_cap, 
                   price_change_pct_24h, circulating_supply 
            FROM gold.top_10_coins 
            ORDER BY market_cap DESC
        """)
        top10['price_usd_display'] = top10['price_usd'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
        top10['market_cap_display'] = top10['market_cap'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A")
        top10['price_change_display'] = top10['price_change_pct_24h'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
        st.dataframe(
            top10[['rank', 'symbol', 'name', 'price_usd_display', 
                   'market_cap_display', 'price_change_display']],
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.error(f"Failed to load top 10 coins: {e}")

# ---- Right: Market Sentiment & Trends ----
with right_col:
    st.subheader("📊 Market Trends")
    try:
        trends_df = load_query("SELECT * FROM gold.market_trends")
        for _, row in trends_df.iterrows():
            st.metric(
                label=row['trend_type'].replace('_', ' ').title(),
                value=row['trend_value'],
                delta=f"{row['numeric_value']:.2f}" if pd.notna(row['numeric_value']) else "N/A",
                delta_color="normal"
            )
            st.info(f"ℹ️ {row['insight']}")
    except Exception as e:
        st.error(f"Failed to load market trends: {e}")

st.markdown("---")

# ---- Bottom Row: Gainers vs Losers ----
col_gain, col_loss = st.columns(2)

with col_gain:
    st.subheader("🚀 Top Gainers (24h)")
    try:
        gainers = load_query("""
            SELECT symbol, name, price_change_pct_24h 
            FROM gold.top_gainers_losers 
            WHERE trend = 'GAINER' 
            ORDER BY price_change_pct_24h DESC 
            LIMIT 10
        """)
        gainers['price_change_display'] = gainers['price_change_pct_24h'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
        st.dataframe(
            gainers[['symbol', 'name', 'price_change_display']],
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.error(f"Failed to load gainers: {e}")

with col_loss:
    st.subheader("🔻 Top Losers (24h)")
    try:
        losers = load_query("""
            SELECT symbol, name, price_change_pct_24h 
            FROM gold.top_gainers_losers 
            WHERE trend = 'LOSER' 
            ORDER BY price_change_pct_24h ASC 
            LIMIT 10
        """)
        losers['price_change_display'] = losers['price_change_pct_24h'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
        st.dataframe(
            losers[['symbol', 'name', 'price_change_display']],
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.error(f"Failed to load losers: {e}")

st.markdown("---")

# ---- Volume Analysis Table ----
st.subheader("💹 Volume Analysis (Top 20 by Volume)")
try:
    volume_df = load_query("""
        SELECT symbol, name, volume_24h, market_cap, vol_to_mcap_ratio, volume_category
        FROM gold.volume_analysis
        ORDER BY volume_24h DESC
    """)
    volume_df['volume_display'] = volume_df['volume_24h'].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A"
    )
    volume_df['mcap_display'] = volume_df['market_cap'].apply(
        lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A"
    )
    volume_df['ratio_display'] = volume_df['vol_to_mcap_ratio'].apply(
        lambda x: f"{x:.4f}" if pd.notna(x) else "N/A"
    )
    st.dataframe(
        volume_df[['symbol', 'name', 'volume_display', 'mcap_display', 
                   'ratio_display', 'volume_category']],
        use_container_width=True,
        hide_index=True
    )
except Exception as e:
    st.error(f"Failed to load volume analysis: {e}")

# Footer
st.markdown("---")
st.caption("Powered by CoinGecko API | Medallion Architecture (Bronze → Silver → Gold) | Postgres on Docker")