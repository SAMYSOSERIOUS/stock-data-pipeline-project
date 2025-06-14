import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from gcs_loader.load_symbols import load_symbols_from_gcs

def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get 12 months of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        hist = ticker.history(start=start_date, end=end_date)

        hist.reset_index(inplace=True)
        info_df = pd.DataFrame([info])
        
        # Verify we have enough data
        if len(hist) < 252:  # Typical number of trading days in a year
            print(f"⚠️  {symbol}: Only {len(hist)} days of data available")
            
        return info_df, hist
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None, None

if __name__ == "__main__":
    symbols = load_symbols_from_gcs()
    for symbol in symbols[:3]:  # Limit for test
        info_df, hist_df = fetch_stock_data(symbol)
        if info_df is not None:
            print(f"{symbol} info:\n{info_df[['symbol','marketCap','sector']].head()}")
        if hist_df is not None:
            print(f"{symbol} history:\n{hist_df[['Date','Close']].head()}\n...{len(hist_df)} days total")
