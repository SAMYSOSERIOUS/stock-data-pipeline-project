import streamlit as st

# IMPORTANT: set_page_config must be the first Streamlit command
st.set_page_config(
    page_title="S&P 500 Stock Times | Home",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import altair as alt
import yaml
import os
import io
from datetime import datetime, timedelta

# Status container for showing only errors
error_status = st.sidebar.empty()

try:
    # Set Google Cloud credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "c:/stock-data-pipeline-project/gcs-key.json"
    
    # Import GCSFileSystem with error handling
    try:
        from gcsfs import GCSFileSystem
    except ImportError:
        error_status.error("❌ Failed to import gcsfs. Please install it with: pip install gcsfs")
        st.stop()
    
    # Load config with error handling
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        error_status.error(f"❌ Error loading config: {str(e)}")
        st.stop()
    
    # Access bucket with error handling
    try:
        bucket = config["gcs"]["bucket_name"]
        fs = GCSFileSystem()
    except Exception as e:
        error_status.error(f"❌ Error connecting to GCS: {str(e)}")
        bucket = None
        fs = None
except Exception as e:
    error_status.error(f"Initialization error: {str(e)}")

# Import and apply shared theme
from style import apply_theme
from utils import add_navigation_footer, add_sidebar_analytics
apply_theme()

# Title and Overview
st.markdown('<h1 class="header-style">S&P 500 Market Overview</h1>', unsafe_allow_html=True)

# Load market overview data with enhanced error handling
def load_market_data(progress_bar=None, status_text=None):
    try:
        # Check if GCS connection is available
        if bucket is None or fs is None:
            st.error("❌ GCS connection not available. Cannot load market data.")
            return pd.DataFrame()
          # Try to load symbols.csv
        try:
            symbols_path = f"gs://{bucket}/symbols.csv"
            if not fs.exists(symbols_path):
                st.error(f"❌ File not found: {symbols_path}")
                return pd.DataFrame()
            symbols = pd.read_csv(symbols_path).symbol.tolist()
        except Exception as e:
            st.error(f"❌ Error loading symbols: {str(e)}")
            return pd.DataFrame()
        
        market_data = []
        for i, symbol in enumerate(symbols):
            try:
                hist_path = f"gs://{bucket}/data/{symbol}_hist.csv"
                if fs.exists(hist_path):
                    df = pd.read_csv(hist_path)
                    if not df.empty and len(df) > 1:
                        df['Return'] = df['Close'].pct_change()
                        last_row = df.iloc[-1]
                        prev_row = df.iloc[-2]
                        market_data.append({
                            'Symbol': symbol,
                            'Last_Close': last_row['Close'],
                            'Daily_Return': last_row['Return'],
                            'Volume': last_row['Volume'],
                            'Change': last_row['Close'] - prev_row['Close'],
                            'High_52W': df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max(),
                            'Low_52W': df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()
                        })
                # Update progress if bars are provided
                if progress_bar is not None and status_text is not None:
                    progress = (i + 1) / len(symbols)
                    progress_bar.progress(progress)
                    status_text.text(f"Loading market data... {symbol} ({i+1}/{len(symbols)})")
            except Exception as e:
                st.warning(f"⚠️ Error processing symbol {symbol}: {str(e)}")
                continue  # Skip problematic symbols
        
        if not market_data:
            st.warning("⚠️ No market data was loaded. Check GCS bucket contents.")
            return pd.DataFrame()
            
        return pd.DataFrame(market_data)
    except Exception as e:
        st.error(f"❌ Error loading market data: {str(e)}")
        return pd.DataFrame()

# Progress tracking moved outside cache
def get_market_df():
    progress_bar = st.progress(0)
    status_text = st.empty()
    df = load_market_data(progress_bar, status_text)
    progress_bar.empty()
    status_text.empty()
    return df

def get_demo_data():
    """Generate demo data if real data cannot be loaded"""
    st.warning("⚠️ Using demo data since real data cannot be loaded.")
    
    # Create some placeholder data
    symbols = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA', 'JNJ', 'V', 'PG']
    import numpy as np
    np.random.seed(42)  # For reproducibility
    
    demo_data = []
    for symbol in symbols:
        close = np.random.uniform(100, 500)
        change = np.random.uniform(-20, 20)
        prev_close = close - change
        return_val = change / prev_close
        
        demo_data.append({
            'Symbol': symbol,
            'Last_Close': close,
            'Daily_Return': return_val,
            'Volume': np.random.randint(500000, 10000000),
            'Change': change,
            'High_52W': close * 1.2,
            'Low_52W': close * 0.8
        })
    
    return pd.DataFrame(demo_data)

# Get market data with fallback to demo data
market_df = get_market_df()

# Enhanced error handling
if market_df.empty:
    st.error("Unable to load market data. Falling back to demo mode.")
    market_df = get_demo_data()
    if market_df.empty:
        st.error("Critical error: Cannot load demo data either.")
        st.stop()

# Market Summary with enhanced metrics
st.subheader("📊 Market Summary")
col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_return = market_df['Daily_Return'].mean()
    st.metric("Market Direction", 
             "🐂 Bullish" if avg_return > 0 else "🐻 Bearish",
             f"{avg_return:.2%}",
             delta_color="normal")

with col2:
    top_gainer = market_df.loc[market_df['Daily_Return'].idxmax()]
    st.metric("Top Gainer", 
             top_gainer['Symbol'],
             f"{top_gainer['Daily_Return']:.2%}",
             delta_color="normal")

with col3:
    top_decliner = market_df.loc[market_df['Daily_Return'].idxmin()]
    st.metric("Top Decliner",
             top_decliner['Symbol'],
             f"{top_decliner['Daily_Return']:.2%}",
             delta_color="inverse")

with col4:
    total_volume = market_df['Volume'].sum()
    st.metric("Total Volume",
             f"{total_volume/1e9:.1f}B",
             f"{len(market_df)} stocks")

# Market Statistics
st.subheader("📈 Market Statistics")
col1, col2 = st.columns(2)

with col1:
    positive_stocks = len(market_df[market_df['Daily_Return'] > 0])
    negative_stocks = len(market_df[market_df['Daily_Return'] < 0])
    
    st.metric("Advancing Stocks", positive_stocks)
    st.metric("Declining Stocks", negative_stocks)
    
    if positive_stocks + negative_stocks > 0:
        advance_decline_ratio = positive_stocks / (positive_stocks + negative_stocks)
        st.metric("Advance/Decline Ratio", f"{advance_decline_ratio:.2%}")

with col2:
    if len(market_df) > 0:
        st.metric("Average Price", f"${market_df['Last_Close'].mean():.2f}")
        st.metric("Price Range", f"${market_df['Last_Close'].min():.2f} - ${market_df['Last_Close'].max():.2f}")
        volatility = market_df['Daily_Return'].std()
        st.metric("Market Volatility", f"{volatility:.2%}")

# Enhanced Market Heatmap
st.subheader("🔥 Market Heatmap")

# Create market performance visualization
heatmap_data = market_df.copy()
heatmap_data['Return_Bucket'] = pd.cut(heatmap_data['Daily_Return'], 
                                      bins=[-1, -0.05, -0.02, 0, 0.02, 0.05, 1],
                                      labels=['Strong Decline', 'Decline', 'Weak Decline', 
                                             'Weak Gain', 'Gain', 'Strong Gain'])

# Interactive scatter plot
scatter = alt.Chart(heatmap_data).mark_circle(size=100).encode(
    x=alt.X('Volume:Q', 
           scale=alt.Scale(type='log'),
           axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0', title='Volume (Log Scale)')),
    y=alt.Y('Daily_Return:Q', 
           axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0', title='Daily Return')),
    color=alt.Color('Daily_Return:Q',
                   scale=alt.Scale(scheme='redblue', domain=[-0.1, 0.1])),
    size=alt.Size('Last_Close:Q', scale=alt.Scale(range=[50, 400])),
    tooltip=['Symbol:N', 
            alt.Tooltip('Last_Close:Q', format='$.2f', title='Price'),
            alt.Tooltip('Daily_Return:Q', format='.2%', title='Return'),
            alt.Tooltip('Volume:Q', format=',.0f', title='Volume'),
            alt.Tooltip('Change:Q', format='$.2f', title='Price Change')]
).properties(
    width=800,
    height=400,
    background='#1A1B26',
    title=alt.TitleParams(text="Stock Performance vs Volume", color='#E0E0E0')
).configure_view(
    strokeWidth=0
).interactive()

st.altair_chart(scatter, use_container_width=True)

# Enhanced Top Performers Section
st.subheader("🏆 Top Performers")

# Create tabs for different views
tab1, tab2, tab3 = st.tabs(["🔥 Most Active", "📈 Top Gainers", "📉 Top Decliners"])

with tab1:
    most_active = market_df.nlargest(15, 'Volume')
    
    active_chart = alt.Chart(most_active).mark_bar().encode(
        x=alt.X('Volume:Q', 
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0', title='Volume')),
        y=alt.Y('Symbol:N', 
               sort='-x',
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0')),
        color=alt.Color('Daily_Return:Q',
                       scale=alt.Scale(scheme='redblue', domain=[-0.05, 0.05])),
        tooltip=['Symbol:N', 
                alt.Tooltip('Volume:Q', format=',.0f'),
                alt.Tooltip('Daily_Return:Q', format='.2%'),
                alt.Tooltip('Last_Close:Q', format='$.2f')]
    ).properties(
        width=700,
        height=400,
        background='#1A1B26',
        title=alt.TitleParams(text="Most Active Stocks by Volume", color='#E0E0E0')
    ).configure_view(strokeWidth=0)
    
    st.altair_chart(active_chart, use_container_width=True)

with tab2:
    top_gainers = market_df.nlargest(15, 'Daily_Return')
    
    gainer_chart = alt.Chart(top_gainers).mark_bar(color='#00FF9F').encode(
        x=alt.X('Daily_Return:Q', 
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0', title='Daily Return')),
        y=alt.Y('Symbol:N', 
               sort='-x',
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0')),
        tooltip=['Symbol:N', 
                alt.Tooltip('Daily_Return:Q', format='.2%'),
                alt.Tooltip('Last_Close:Q', format='$.2f'),
                alt.Tooltip('Volume:Q', format=',.0f')]
    ).properties(
        width=700,
        height=400,
        background='#1A1B26',
        title=alt.TitleParams(text="Top Gaining Stocks", color='#E0E0E0')
    ).configure_view(strokeWidth=0)
    
    st.altair_chart(gainer_chart, use_container_width=True)

with tab3:
    top_decliners = market_df.nsmallest(15, 'Daily_Return')
    
    decliner_chart = alt.Chart(top_decliners).mark_bar(color='#FF5B5B').encode(
        x=alt.X('Daily_Return:Q', 
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0', title='Daily Return')),
        y=alt.Y('Symbol:N', 
               sort='x',
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0')),
        tooltip=['Symbol:N', 
                alt.Tooltip('Daily_Return:Q', format='.2%'),
                alt.Tooltip('Last_Close:Q', format='$.2f'),
                alt.Tooltip('Volume:Q', format=',.0f')]
    ).properties(
        width=700,
        height=400,
        background='#1A1B26',
        title=alt.TitleParams(text="Top Declining Stocks", color='#E0E0E0')
    ).configure_view(strokeWidth=0)
    
    st.altair_chart(decliner_chart, use_container_width=True)

# Enhanced Sidebar Navigation
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    
    # Quick navigation with icons
    nav_items = [
        ("📊", "Analysis", "Detailed stock analysis with predictions"),
        ("📰", "News", "Latest market news and articles"),
        ("🌎", "Geography", "Geographic distribution of companies")
    ]
    
    for icon, page, description in nav_items:
        with st.container():
            st.markdown(f"""
            <div style="padding: 0.5rem; margin: 0.25rem 0; border-radius: 5px; 
                        background-color: #2F3136; border-left: 3px solid #00ADB5;">
                <a href="{page}" style="text-decoration: none; color: #E0E0E0;">
                    <strong>{icon} {page}</strong><br>
                    <small style="color: #A0A0A0;">{description}</small>
                </a>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Enhanced Market Insights
    st.markdown("### 📊 Market Insights")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active Stocks", len(market_df))
        st.metric("Avg Volume", f"{market_df['Volume'].mean()/1e6:.1f}M")
    
    with col2:
        pos_count = len(market_df[market_df['Daily_Return'] > 0])
        st.metric("Positive", pos_count)
        st.metric("Negative", len(market_df) - pos_count)
    
    # Market Sentiment Gauge
    sentiment_score = market_df['Daily_Return'].mean()
    sentiment_color = "#00FF9F" if sentiment_score > 0 else "#FF5B5B"
    
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background-color: #2F3136; 
                border-radius: 5px; margin: 1rem 0;">
        <h4 style="color: #E0E0E0; margin-bottom: 0.5rem;">Market Sentiment</h4>
        <div style="font-size: 2rem; color: {sentiment_color}; font-weight: bold;">
            {sentiment_score:.2%}
        </div>
        <div style="color: #A0A0A0; font-size: 0.9rem;">
            {"Bullish Market" if sentiment_score > 0 else "Bearish Market"}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Stock Lookup with enhanced features
    st.markdown("### 🔍 Quick Stock Lookup")
    
    # Search functionality
    search_term = st.text_input("Search by symbol:", placeholder="e.g., AAPL")
    
    if search_term:
        filtered_stocks = market_df[market_df['Symbol'].str.contains(search_term.upper(), na=False)]
        if not filtered_stocks.empty:
            for _, stock in filtered_stocks.head(3).iterrows():
                change_color = "#00FF9F" if stock['Daily_Return'] > 0 else "#FF5B5B"
                st.markdown(f"""
                <div style="padding: 0.5rem; margin: 0.25rem 0; background-color: #2F3136; 
                            border-radius: 5px; border-left: 3px solid {change_color};">
                    <strong style="color: #E0E0E0;">{stock['Symbol']}</strong><br>
                    <span style="color: #A0A0A0;">${stock['Last_Close']:.2f}</span>
                    <span style="color: {change_color}; margin-left: 10px;">
                        {stock['Daily_Return']:.2%}
                    </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No stocks found matching your search.")
    
    # Random stock picker
    if st.button("🎲 Random Stock", help="Get a random stock from the market"):
        random_stock = market_df.sample(1).iloc[0]
        change_color = "#00FF9F" if random_stock['Daily_Return'] > 0 else "#FF5B5B"
        st.markdown(f"""
        <div style="padding: 1rem; background-color: #2F3136; border-radius: 5px; 
                    border: 2px solid #00ADB5; text-align: center;">
            <h3 style="color: #00ADB5; margin-bottom: 0.5rem;">{random_stock['Symbol']}</h3>
            <div style="color: #E0E0E0; font-size: 1.5rem; font-weight: bold;">
                ${random_stock['Last_Close']:.2f}
            </div>
            <div style="color: {change_color}; font-size: 1.2rem; margin-top: 0.25rem;">
                {random_stock['Daily_Return']:.2%}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Add navigation footer and sidebar analytics
add_navigation_footer()
add_sidebar_analytics(market_df)
