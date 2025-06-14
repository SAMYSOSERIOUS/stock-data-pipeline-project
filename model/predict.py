import joblib
import pandas as pd
import numpy as np
from gcsfs import GCSFileSystem
import yaml
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='xgboost')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Set GCS credentials environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(project_root, config["gcs"]["gcp_credentials_path"])

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_features(df):
    df = df.copy()
    # Use the same windows as in train.py
    for window in [3, 5, 10, 15]:
        df[f'Returns_{window}d'] = df['Close'].pct_change(window)
        df[f'Volatility_{window}d'] = df[f'Returns_{window}d'].rolling(window=window).std()
        df[f'MA_{window}d'] = df['Close'].rolling(window=window).mean()
        df[f'Volume_MA_{window}d'] = df['Volume'].rolling(window=window).mean()
        df[f'High_{window}d'] = df['High'].rolling(window=window).max()
        df[f'Low_{window}d'] = df['Low'].rolling(window=window).min()
    
    # Technical indicators
    df['RSI'] = calculate_rsi(df['Close'], period=14)
    df['RSI_MA'] = df['RSI'].rolling(window=10).mean()
    
    # Price ratios and momentum
    df['HL_Ratio'] = df['High'] / df['Low']
    df['CO_Ratio'] = df['Close'] / df['Open']
    df['Price_Momentum'] = df['Close'] - df['Close'].shift(10)
    df['Volume_Momentum'] = df['Volume'] - df['Volume'].shift(10)
    
    # Trend indicators
    df['Upper_Channel'] = df['High'].rolling(20).max()
    df['Lower_Channel'] = df['Low'].rolling(20).min()
    df['Channel_Position'] = (df['Close'] - df['Lower_Channel']) / (df['Upper_Channel'] - df['Lower_Channel'])
    
    return df

def plot_predictions(symbol, dates, actual, predicted, error_pct, save_path):
    plt.figure(figsize=(15, 10))
    
    # Plot actual and predicted values
    plt.subplot(2, 1, 1)
    plt.plot(dates, actual, label='Actual', marker='o')
    plt.plot(dates, predicted, label='Predicted', marker='x')
    plt.title(f'{symbol} Stock Price Predictions')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    
    # Plot prediction error percentage
    plt.subplot(2, 1, 2)
    plt.bar(dates, error_pct)
    plt.title('Prediction Error Percentage')
    plt.xlabel('Date')
    plt.ylabel('Error %')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def predict(symbol, forecast_days=3):
    try:
        print(f"\n=== Making Predictions for {symbol} ===")
        
        # Initialize GCS filesystem with proper authentication
        fs = GCSFileSystem()
        bucket_name = config["gcs"]["bucket_name"]
        
        model_path = f"{bucket_name}/models/{symbol}_model.pkl"
        scaler_path = f"{bucket_name}/models/{symbol}_scaler.pkl"
        data_path = f"{bucket_name}/data/{symbol}_hist.csv"
        selected_features_path = f"{bucket_name}/models/{symbol}_selected_features.txt"

        required_files = [model_path, scaler_path, data_path, selected_features_path]
        for file_path in required_files:
            if not fs.exists(file_path):
                print(f"Missing required file: {file_path}")
                return

        print("\nLoading model and data...")
        
        # Ensure /tmp directory exists
        tmp_dir = os.path.join(os.path.abspath(os.sep), 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        # Download necessary files
        local_model_path = os.path.join(tmp_dir, f"{symbol}_model.pkl")
        local_scaler_path = os.path.join(tmp_dir, f"{symbol}_scaler.pkl")
        local_selected_features_path = os.path.join(tmp_dir, f"{symbol}_selected_features.txt")
        fs.get(model_path, local_model_path)
        fs.get(scaler_path, local_scaler_path)
        fs.get(selected_features_path, local_selected_features_path)
        
        model = joblib.load(local_model_path)
        scaler = joblib.load(local_scaler_path)
        with open(local_selected_features_path) as f:
            selected_features = [line.strip() for line in f if line.strip()]

        # Load data
        df = pd.read_csv(f"gs://{data_path}")

        # Convert dates and ensure data is sorted
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], utc=True)
            df = df.sort_values('Date')

        print("\nGenerating features...")
        df = add_features(df)
        df = df.dropna().reset_index(drop=True)

        # Get feature columns (same as in training)
        feature_cols = [col for col in df.columns if col not in ['Date', 'Close']]

        # Select test set as last N rows (N = 31, matching your last train.py run)
        test_size = 31
        X_test = df.iloc[-test_size:][selected_features]
        y_test = df.iloc[-test_size:]['Close']
        test_dates_aligned = df.iloc[-test_size:]['Date']

        if X_test.empty:
            print("No test data found. Check your pipeline.")
            return

        # Normalize test features
        X_test_norm = pd.DataFrame(
            scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index
        )

        # Make predictions
        print("\nMaking predictions...")
        predictions = model.predict(X_test_norm)

        # Create output DataFrame with comprehensive metrics
        out_df = pd.DataFrame({
            "Date": test_dates_aligned,
            "Actual": y_test,
            "Predicted": predictions,
            "Error": y_test - predictions,
            "Error_Pct": ((y_test - predictions) / y_test) * 100,
            "Direction_Actual": np.sign(y_test.diff()),
            "Direction_Predicted": np.sign(predictions - y_test.shift())
        })

        # --- Forecast future dates ---
        print(f"\nForecasting {forecast_days} future days...")
        rolling_df = df.copy()  # This will be extended with forecasted rows
        future_rows = []
        for i in range(forecast_days):
            # 1. Create a new row for the next day
            last_row = rolling_df.iloc[-1].copy()
            next_date = last_row['Date'] + pd.tseries.offsets.BDay(1)
            # Build a new row for the next day
            new_row = last_row.copy()
            new_row['Date'] = next_date
            # Use the last predicted close for rolling features
            prev_closes = rolling_df['Close'].tolist()
            # For the first forecast, use last real close; for subsequent, use last predicted
            if i == 0:
                prev_close = last_row['Close']
            else:
                prev_close = rolling_df.iloc[-1]['Close']
            # Set Close to previous prediction (will be overwritten after prediction)
            new_row['Close'] = prev_close
            # For rolling features, append the last predicted close to the rolling window
            closes = prev_closes + [prev_close]
            # Update rolling features
            for window in [3, 5, 10, 15]:
                if len(closes) >= window:
                    new_row[f'MA_{window}d'] = pd.Series(closes[-window:]).mean()
                    new_row[f'Returns_{window}d'] = (closes[-1] - closes[-window]) / closes[-window]
                    new_row[f'Volatility_{window}d'] = pd.Series(closes[-window:]).pct_change().std()
                if f'Volume_MA_{window}d' in new_row:
                    vols = rolling_df['Volume'].tolist()[-window:]
                    if len(vols) == window:
                        new_row[f'Volume_MA_{window}d'] = pd.Series(vols).mean()
                if f'High_{window}d' in new_row:
                    highs = rolling_df['High'].tolist()[-window:]
                    if len(highs) == window:
                        new_row[f'High_{window}d'] = max(highs)
                if f'Low_{window}d' in new_row:
                    lows = rolling_df['Low'].tolist()[-window:]
                    if len(lows) == window:
                        new_row[f'Low_{window}d'] = min(lows)
            # RSI and other features
            # For RSI, recalc using last 14 closes (including prediction)
            if len(closes) >= 14:
                rsi_series = pd.Series(closes[-14:])
                delta = rsi_series.diff()
                gain = (delta.where(delta > 0, 0)).mean()
                loss = (-delta.where(delta < 0, 0)).mean()
                rs = gain / loss if loss != 0 else 0
                new_row['RSI'] = 100 - (100 / (1 + rs)) if loss != 0 else 100
            # RSI_MA
            if 'RSI' in new_row and not pd.isna(new_row['RSI']):
                rsi_hist = list(rolling_df['RSI'].dropna().values)[-9:] + [new_row['RSI']]
                if len(rsi_hist) == 10:
                    new_row['RSI_MA'] = pd.Series(rsi_hist).mean()
            # Price ratios and momentum
            if len(closes) >= 10:
                new_row['Price_Momentum'] = closes[-1] - closes[-10]
            if 'Volume' in rolling_df.columns and len(rolling_df['Volume']) >= 10:
                new_row['Volume_Momentum'] = rolling_df['Volume'].iloc[-1] - rolling_df['Volume'].iloc[-10]
            # Trend indicators
            if 'High' in rolling_df.columns and len(rolling_df['High']) >= 20:
                new_row['Upper_Channel'] = max(rolling_df['High'].tolist()[-20:])
            if 'Low' in rolling_df.columns and len(rolling_df['Low']) >= 20:
                new_row['Lower_Channel'] = min(rolling_df['Low'].tolist()[-20:])
            if 'Upper_Channel' in new_row and 'Lower_Channel' in new_row and (new_row['Upper_Channel'] - new_row['Lower_Channel']) != 0:
                new_row['Channel_Position'] = (new_row['Close'] - new_row['Lower_Channel']) / (new_row['Upper_Channel'] - new_row['Lower_Channel'])
            # Prepare input for model
            X_future = pd.DataFrame([new_row[selected_features]])
            X_future_norm = pd.DataFrame(scaler.transform(X_future), columns=X_future.columns)
            pred = model.predict(X_future_norm)[0]
            new_row['Close'] = pred  # Now set the predicted close
            # Append new_row to rolling_df for the next iteration
            rolling_df = pd.concat([rolling_df, pd.DataFrame([new_row])], ignore_index=True)
            # Save forecast row for output
            future_rows.append({
                "Date": next_date,
                "Actual": np.nan,
                "Predicted": pred,
                "Error": np.nan,
                "Error_Pct": np.nan,
                "Direction_Actual": np.nan,
                "Direction_Predicted": np.nan
            })
        if future_rows:
            out_df = pd.concat([out_df, pd.DataFrame(future_rows)], ignore_index=True)

        # Calculate comprehensive performance metrics
        metrics = {
            "MSE": ((out_df["Actual"] - out_df["Predicted"]) ** 2).mean(),
            "RMSE": np.sqrt(((out_df["Actual"] - out_df["Predicted"]) ** 2).mean()),
            "MAE": np.abs(out_df["Actual"] - out_df["Predicted"]).mean(),
            "MAPE": np.abs((out_df["Actual"] - out_df["Predicted"]) / out_df["Actual"]).mean() * 100,
            "Direction_Accuracy": (out_df["Direction_Actual"] == out_df["Direction_Predicted"]).mean() * 100
        }
        
        print("\n=== Prediction Performance Metrics ===")
        print(f"MSE: {metrics['MSE']:.4f}")
        print(f"RMSE: {metrics['RMSE']:.4f}")
        print(f"MAE: {metrics['MAE']:.4f}")
        print(f"MAPE: {metrics['MAPE']:.2f}%")
        print(f"Direction Accuracy: {metrics['Direction_Accuracy']:.2f}%")

        # Generate and save prediction plot
        print("\nGenerating visualization...")
        plot_path = os.path.join(tmp_dir, f"{symbol}_predictions.png")
        plot_predictions(
            symbol,
            out_df["Date"],
            out_df["Actual"],
            out_df["Predicted"],
            out_df["Error_Pct"],
            plot_path
        )

        # Save predictions, metrics, and plot
        print("\nSaving results...")
        pred_path = os.path.join(tmp_dir, f"{symbol}_predictions.csv")
        metrics_path = os.path.join(tmp_dir, f"{symbol}_metrics.csv")
        
        out_df.to_csv(pred_path, index=False)
        pd.DataFrame([metrics]).to_csv(metrics_path, index=False)
        
        fs.put(pred_path, f"{bucket_name}/predictions/{symbol}_predictions.csv")
        fs.put(metrics_path, f"{bucket_name}/predictions/{symbol}_metrics.csv")
        fs.put(plot_path, f"{bucket_name}/predictions/{symbol}_predictions.png")
        
        print(f"\nAll results saved to GCS bucket: {bucket_name}")
        print("├── predictions/")
        print(f"│   ├── {symbol}_predictions.csv")
        print(f"│   ├── {symbol}_metrics.csv")
        print(f"│   └── {symbol}_predictions.png")

    except Exception as e:
        print(f"\nError in predict: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python predict.py <symbol>")
        print("Example: python predict.py AAPL")
        sys.exit(1)
    predict(sys.argv[1])
