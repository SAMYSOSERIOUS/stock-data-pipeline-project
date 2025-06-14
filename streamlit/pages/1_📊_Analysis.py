import streamlit as st
import pandas as pd
from gcsfs import GCSFileSystem
import yaml
import os
import io
import altair as alt
import matplotlib.pyplot as plt
from style import apply_theme
from utils import add_navigation_footer, show_error_message, format_large_number

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "c:/stock-data-pipeline-project/gcs-key.json"

# Find project root and load config.yaml
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_path = os.path.join(project_root, "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Access bucket
bucket = config["gcs"]["bucket_name"]
fs = GCSFileSystem()
symbols = pd.read_csv(f"gs://{bucket}/symbols.csv").symbol.tolist()

st.set_page_config(
    page_title="Detailed Analysis | S&P 500 Stocks", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# Apply shared theme
apply_theme()

st.title("📊 Detailed Stock Analysis")
st.markdown("---")

# Enhanced stock selector with search
col_select, col_search = st.columns([1, 1])

with col_select:
    symbol = st.selectbox("Select stock:", symbols, help="Choose a stock symbol for detailed analysis")

with col_search:
    search_term = st.text_input("🔍 Search stocks:", placeholder="e.g., AAPL, Microsoft")
    if search_term:
        filtered_symbols = [s for s in symbols if search_term.upper() in s.upper()]
        if filtered_symbols:
            symbol = st.selectbox("Search results:", filtered_symbols, key="search_results")

# Load and display company information
@st.cache(ttl=3600, allow_output_mutation=True)
def load_company_info(symbol):
    info_path = f"gs://{config['gcs']['bucket_name']}/data/{symbol}_info.csv"
    if fs.exists(info_path):
        try:
            info_df = pd.read_csv(info_path)
            return info_df.iloc[0] if not info_df.empty else None
        except Exception:
            return None
    return None

company_info = load_company_info(symbol)
if company_info is not None and 'longName' in company_info:
    st.markdown(f"""
    <div style="padding: 1rem; background-color: #2F3136; border-radius: 5px; 
                border-left: 4px solid #00ADB5; margin: 1rem 0;">
        <h3 style="color: #00ADB5; margin-bottom: 0.5rem;">{company_info['longName']}</h3>
        <p style="color: #A0A0A0; margin: 0;">
            {company_info.get('sector', 'Unknown Sector')} | {company_info.get('industry', 'Unknown Industry')}
        </p>
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Prediction vs Actual")
    pred_path = f"gs://{config['gcs']['bucket_name']}/predictions/{symbol}_predictions.csv"
    hist_path = f"gs://{config['gcs']['bucket_name']}/data/{symbol}_hist.csv"
    residual_path = f"bucket500stocks/plots/{symbol}_residuals.png"
    
    try:
        if fs.exists(pred_path):
            # Load and prepare the prediction data
            df = pd.read_csv(pred_path)
            
            # Handle time series data if Date column exists
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df = df.sort_values("Date")
                df.set_index("Date", inplace=True)
            
            # Show last 252 trading days (approx. 1 year) if available, but only if at least 200 points
            chart_window = 252
            min_points = 200
            if len(df) >= min_points:
                df_chart = df.tail(chart_window)
            else:
                df_chart = df
            # Custom matplotlib plot for actual, predicted, and forecast
            actual_col = None
            pred_col = None
            if set(["target", "prediction"]).issubset(df.columns):
                actual_col, pred_col = "target", "prediction"
            elif set(["Actual", "Predicted"]).issubset(df.columns):
                actual_col, pred_col = "Actual", "Predicted"
            if actual_col and pred_col:
                # Split into historical and forecast
                historical = df_chart[df_chart[actual_col].notna()]
                forecast = df_chart[df_chart[actual_col].isna()]
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(historical.index, historical[actual_col], label="Actual", color="#1f77b4", linewidth=2)
                ax.plot(historical.index, historical[pred_col], label="Predicted", color="#ff7f0e", linewidth=2)
                if not forecast.empty:
                    ax.plot(forecast.index, forecast[pred_col], label="Forecast", color="#2ca02c", linestyle="dashed", linewidth=2)
                    # Vertical line for last real date
                    ax.axvline(historical.index[-1], color="red", linestyle="dotted", linewidth=2, label="Forecast Start")
                ax.legend()
                ax.set_title("Prediction vs Actual (with Forecast)")
                ax.set_ylabel("Price")
                ax.set_xlabel("Date")
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
            elif actual_col:
                st.line_chart(df_chart[[actual_col]])
            else:
                st.warning("Missing required columns (target/prediction or Actual/Predicted) in the prediction data.")
        else:
            st.warning(f"No prediction data available for {symbol}")
    except Exception as e:
        st.error(f"Error processing prediction data: {str(e)}")
        st.subheader("Residual Analysis")
        if fs.exists(residual_path):
            with fs.open(residual_path, "rb") as fimg:
                st.image(io.BytesIO(fimg.read()), caption="Residual Plot")
        else:
            st.warning("Residual plot not available.")

# Move business insights and metrics outside of col1/col2
# Load historical data for insights
hist_df = pd.read_csv(hist_path) if fs.exists(hist_path) else None
st.subheader("📈 Business Insights & Technical Analysis")
if hist_df is not None:
    hist_df["Return"] = hist_df["Close"].pct_change()
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Average Daily Return", f"{hist_df['Return'].mean():.4%}")
        st.caption("📘 The mean percentage change in stock price over one trading day")
    with m2:
        volatility = hist_df['Return'].std()
        st.metric("Volatility", f"{volatility:.4%}")
        st.caption("📊 A measure of price variability. Higher values indicate greater price swings")
    with m3:
        # Compute momentum as percent change over last 3 real (non-NaN Actual) predicted values
        momentum = "N/A"
        if 'df' in locals():
            pred_col = None
            if 'prediction' in df.columns:
                pred_col = 'prediction'
            elif 'Predicted' in df.columns:
                pred_col = 'Predicted'
            if pred_col is not None and 'Actual' in df.columns:
                real_mask = df['Actual'].notna()
                real_preds = df.loc[real_mask, pred_col].tail(3)
                if len(real_preds) == 3 and real_preds.iloc[0] != 0:
                    momentum_val = (real_preds.iloc[-1] - real_preds.iloc[0]) / abs(real_preds.iloc[0])
                    momentum = f"{momentum_val:.2%}"
        st.metric("Momentum (3-day)", momentum)
        st.caption("🔄 Short-term price movement trend over the last 3 days")
    with m4:
        trend = hist_df['Close'].tail(7).mean() - hist_df['Close'].head(7).mean()
        trend_text = f"{trend:.2f}"
        st.metric("Weekly Trend", trend_text, delta=f"{trend/hist_df['Close'].head(7).mean():.2%}")
        st.caption("📈 Difference between 7-day moving averages")
    # Interactive charts with Altair
    returns_chart = alt.Chart(hist_df).mark_area(
        line={'color':'#00ADB5'},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='#1A1B26', offset=0),
                  alt.GradientStop(color='#00ADB5', offset=1)],
            x1=1,
            x2=1,
            y1=1,
            y2=0
        )
    ).encode(
        x=alt.X('Date:T', 
               title='Date',
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0')),
        y=alt.Y('Return:Q', 
               title='Daily Return',
               axis=alt.Axis(labelColor='#E0E0E0', titleColor='#E0E0E0')),
        tooltip=['Date:T', alt.Tooltip('Return:Q', format='.2%')]
    ).properties(
        title={
            'text': 'Daily Returns Over Time',
            'color': '#E0E0E0'
        },
        height=300,
        background='#1A1B26'
    ).configure_view(
        strokeWidth=0
    ).interactive()
    st.altair_chart(returns_chart, use_container_width=True)

with col2:
    info_path = f"gs://{config['gcs']['bucket_name']}/data/{symbol}_info.csv"
    if fs.exists(info_path):
        info_df = pd.read_csv(info_path)
        if not info_df.empty:
            st.subheader("Key Statistics")
            metrics = {
                "Sector": info_df.iloc[0].get('sector', 'N/A'),
                "Industry": info_df.iloc[0].get('industry', 'N/A'),
                "Market Cap": info_df.iloc[0].get('marketCap', 'N/A'),
                "P/E Ratio": info_df.iloc[0].get('trailingPE', 'N/A'),
                "52 Week High": info_df.iloc[0].get('fiftyTwoWeekHigh', 'N/A'),
                "52 Week Low": info_df.iloc[0].get('fiftyTwoWeekLow', 'N/A')
            }
            
            for key, value in metrics.items():
                if key == "Market Cap" and pd.notna(value):
                    st.metric(key, format_large_number(value))
                else:
                    st.metric(key, value)

# Add navigation footer
add_navigation_footer()
