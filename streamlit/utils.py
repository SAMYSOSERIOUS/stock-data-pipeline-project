import streamlit as st
import pandas as pd
from datetime import datetime

def add_navigation_footer():
    """Add a consistent navigation footer across all pages"""
    st.markdown("---")
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background-color: #1A1B26; 
                border-radius: 5px; margin-top: 2rem;">
        <h4 style="color: #00ADB5; margin-bottom: 1rem;">📊 S&P 500 Stock Analysis Dashboard</h4>
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <a href="/" style="color: #E0E0E0; text-decoration: none;">🏠 Home</a>
            <a href="/Analysis" style="color: #E0E0E0; text-decoration: none;">📊 Analysis</a>
            <a href="/News" style="color: #E0E0E0; text-decoration: none;">📰 News</a>
            <a href="/Geography" style="color: #E0E0E0; text-decoration: none;">🌎 Geography</a>
        </div>
        <div style="margin-top: 1rem; color: #A0A0A0; font-size: 0.9rem;">
            Last updated: {current_time} | 
            Enhanced S&P 500 Data Pipeline with Ridge Regression Forecasting
        </div>
    </div>
    """, unsafe_allow_html=True)

def add_sidebar_analytics(market_df=None):
    """Add analytics to sidebar if market data is available"""
    if market_df is not None and not market_df.empty:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📈 Quick Analytics")
            
            # Market breadth
            positive_count = len(market_df[market_df['Daily_Return'] > 0])
            total_count = len(market_df)
            breadth = positive_count / total_count if total_count > 0 else 0
            
            # Volatility indicator
            volatility = market_df['Daily_Return'].std()
            vol_level = "Low" if volatility < 0.02 else "High" if volatility > 0.05 else "Medium"
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Market Breadth", f"{breadth:.1%}")
                st.metric("Volatility", vol_level)
            
            with col2:
                st.metric("Up/Down", f"{positive_count}/{total_count-positive_count}")
                avg_volume = market_df['Volume'].mean()
                st.metric("Avg Volume", f"{avg_volume/1e6:.0f}M")

def format_large_number(num):
    """Format large numbers with appropriate suffixes"""
    if pd.isna(num):
        return "N/A"
    
    if abs(num) >= 1e12:
        return f"${num/1e12:.2f}T"
    elif abs(num) >= 1e9:
        return f"${num/1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"${num/1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"${num/1e3:.2f}K"
    else:
        return f"${num:.2f}"

def show_loading_message(message="Loading data..."):
    """Show a consistent loading message"""
    return st.info(f"⏳ {message}")

def show_error_message(error, context=""):
    """Show a consistent error message with optional context"""
    if context:
        st.error(f"❌ Error in {context}: {str(error)}")
    else:
        st.error(f"❌ {str(error)}")

def add_page_metrics(title, description=""):
    """Add consistent page header with metrics"""
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #00ADB5 0%, #393E46 100%); 
                padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <h1 style="color: white; margin: 0;">{title}</h1>
        {f'<p style="color: #E0E0E0; margin: 0.5rem 0 0 0;">{description}</p>' if description else ''}
    </div>
    """, unsafe_allow_html=True)
