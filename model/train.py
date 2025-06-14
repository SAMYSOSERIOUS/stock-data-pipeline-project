import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from sklearn.preprocessing import RobustScaler
from sklearn.linear_model import Ridge
import numpy as np
import joblib
import os
from google.cloud import storage
from gcsfs import GCSFileSystem
import yaml
from datetime import datetime, timedelta
from itertools import product
import matplotlib.pyplot as plt
import warnings
from tqdm import tqdm

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Set GCS credentials environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(project_root, config["gcs"]["gcp_credentials_path"])

warnings.filterwarnings('ignore', category=UserWarning, module='xgboost')

def calculate_rsi(prices, period=14):
    # Calculate RSI
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_features(df):
    df = df.copy()
      # Price-based features with different timeframes
    for window in [3, 5, 10, 15]:
        # Returns and volatility
        df[f'Returns_{window}d'] = df['Close'].pct_change(window)
        df[f'Volatility_{window}d'] = df[f'Returns_{window}d'].rolling(window=window).std()
        
        # Moving averages
        df[f'MA_{window}d'] = df['Close'].rolling(window=window).mean()
        df[f'Volume_MA_{window}d'] = df['Volume'].rolling(window=window).mean()
        
        # Price channels
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

def normalize_features(X_train, X_val=None, X_test=None):
    """Normalize features using RobustScaler"""
    scaler = RobustScaler()
    X_train_norm = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    
    transforms = {'scaler': scaler}
    result = {'X_train': X_train_norm}
    
    if X_val is not None:
        X_val_norm = pd.DataFrame(scaler.transform(X_val), columns=X_val.columns, index=X_val.index)
        result['X_val'] = X_val_norm
        
    if X_test is not None:
        X_test_norm = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns, index=X_test.index)
        result['X_test'] = X_test_norm
    
    return result, transforms

def plot_feature_importance(model, feature_names, save_path):
    """Plot and save feature importance"""
    importance = model.feature_importances_
    sorted_idx = np.argsort(importance)
    pos = np.arange(sorted_idx.shape[0]) + .5
    
    plt.figure(figsize=(12, 6))
    plt.barh(pos, importance[sorted_idx])
    plt.yticks(pos, np.array(feature_names)[sorted_idx])
    plt.xlabel('Feature Importance')
    plt.title('XGBoost Feature Importance')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def train_model(symbol):
    try:
        # Ensure /tmp directory exists
        tmp_dir = os.path.join(os.path.abspath(os.sep), 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        # Initialize GCS filesystem with proper authentication
        fs = GCSFileSystem()
        bucket_name = config["gcs"]["bucket_name"]
        
        # Use the hist data from the data/ folder
        gcs_path = f"{bucket_name}/data/{symbol}_hist.csv"
        if not fs.exists(gcs_path):
            print(f"Missing data for {symbol}")
            return

        # Load and sort data
        print(f"Loading data for {symbol}...")
        df = pd.read_csv(f"gs://{gcs_path}")
        if df.shape[0] < 100:
            print(f"Insufficient data points: {df.shape[0]}")
            return
            
        if 'Date' not in df.columns:
            print(f"Date column missing in data for {symbol}")
            return
            
        # Convert dates and sort
        df['Date'] = pd.to_datetime(df['Date'], utc=True)
        df = df.sort_values('Date')
        
        print("\n=== Dataset Overview ===")
        print(f"Symbol: {symbol}")
        print(f"Period: {df['Date'].min().strftime('%Y-%m-%d')} → {df['Date'].max().strftime('%Y-%m-%d')}")
        print(f"Total days: {len(df):,}")
        
        # Add features and handle missing values
        df = add_features(df)
        df = df.dropna().reset_index(drop=True)
        print(f"\n=== Feature Engineering ===")
        print(f"Clean data points: {len(df):,}")
          # Calculate minimum required history for features
        max_window = 20  # Maximum lookback period used in feature generation
        min_train_size = 100  # Minimum ~4 months of training data
        
        # Ensure we have enough data
        if len(df) < (min_train_size + 2 * max_window):
            print(f"Insufficient data points: {len(df)}. Need at least {min_train_size + 2 * max_window} days")
            return
            
        # Calculate split sizes
        total_size = len(df)
        test_size = max(60, int(total_size * 0.2))  # At least 60 days or 20% for test
        val_size = max(30, int(total_size * 0.1))   # At least 30 days or 10% for validation
        
        # Ensure minimum training size is maintained
        remaining_size = total_size - (test_size + val_size)
        if remaining_size < min_train_size:
            print(f"Warning: Adjusting split sizes to ensure minimum training size of {min_train_size} days")
            # Adjust test and validation sizes proportionally
            total_test_val = test_size + val_size
            test_size = int(test_size * (total_size - min_train_size) / total_test_val)
            val_size = int(val_size * (total_size - min_train_size) / total_test_val)
        
        train_end = len(df) - (test_size + val_size)
        val_end = len(df) - test_size
        
        print("\n=== Data Split ===")
        print(f"Training:    {df['Date'].iloc[0].strftime('%Y-%m-%d')} → {df['Date'].iloc[train_end-1].strftime('%Y-%m-%d')} ({train_end:,} days)")
        print(f"Validation:  {df['Date'].iloc[train_end].strftime('%Y-%m-%d')} → {df['Date'].iloc[val_end-1].strftime('%Y-%m-%d')} ({val_size:,} days)")
        print(f"Test:       {df['Date'].iloc[val_end].strftime('%Y-%m-%d')} → {df['Date'].iloc[-1].strftime('%Y-%m-%d')} ({test_size:,} days)")
        
        # Verify no data leakage in feature generation
        df_train = df.iloc[:train_end].copy()
        df_val = df.iloc[train_end:val_end].copy()
        df_test = df.iloc[val_end:].copy()
        
        # Generate features separately for each split to prevent lookback leakage
        df_train = add_features(df_train)
        df_val = add_features(df_val)
        df_test = add_features(df_test)
        
        # Drop NaN rows resulting from feature generation
        df_train = df_train.dropna()
        df_val = df_val.dropna()
        df_test = df_test.dropna()
        
        # Get feature columns
        feature_cols = [col for col in df_train.columns if col not in ['Date', 'Close']]
        
        # Create feature matrices and target vectors
        X_train = df_train[feature_cols]
        y_train = df_train['Close']
        X_val = df_val[feature_cols]
        y_val = df_val['Close']
        X_test = df_test[feature_cols]
        y_test = df_test['Close']
        
        print(f"\nEffective split sizes after feature generation:")
        print(f"Training:   {len(X_train)} samples")
        print(f"Validation: {len(X_val)} samples")
        print(f"Test:      {len(X_test)} samples")
        
        # Select most important features (use all features for Ridge)
        selected_features = feature_cols
        X_train = X_train[selected_features]
        X_val = X_val[selected_features]
        X_test = X_test[selected_features]
        # Save selected features for use in prediction
        selected_features_path = os.path.join(tmp_dir, f"{symbol}_selected_features.txt")
        with open(selected_features_path, "w") as f:
            for feat in selected_features:
                f.write(f"{feat}\n")
        fs.put(selected_features_path, f"{bucket_name}/models/{symbol}_selected_features.txt")
        
        # Normalize features
        normalized_data, transforms = normalize_features(X_train, X_val, X_test)
        X_train_norm = normalized_data['X_train']
        X_val_norm = normalized_data['X_val']
        X_test_norm = normalized_data['X_test']
        
        # Train Ridge regression
        print("\n=== Ridge Regression ===")
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train_norm, y_train)
        ridge_pred = ridge.predict(X_test_norm)
        ridge_mse = mean_squared_error(y_test, ridge_pred)
        ridge_mae = np.mean(np.abs(y_test - ridge_pred))
        ridge_mape = np.mean(np.abs((y_test - ridge_pred) / y_test)) * 100
        ridge_dir_acc = (np.sign(np.diff(y_test)) == np.sign(np.diff(ridge_pred))).mean() * 100
        print(f"Ridge MSE: {ridge_mse:.2f}")
        print(f"Ridge MAE: {ridge_mae:.2f}")
        print(f"Ridge MAPE: {ridge_mape:.2f}%")
        print(f"Ridge Direction Accuracy: {ridge_dir_acc:.2f}%")
        
        # Save Ridge model and scaler
        model_path = os.path.join(tmp_dir, f"{symbol}_ridge_model.pkl")
        scaler_path = os.path.join(tmp_dir, f"{symbol}_scaler.pkl")
        
        joblib.dump(ridge, model_path)
        joblib.dump(transforms['scaler'], scaler_path)
        
        fs.put(model_path, f"{bucket_name}/models/{symbol}_model.pkl")
        fs.put(scaler_path, f"{bucket_name}/models/{symbol}_scaler.pkl")
        
        # Save predictions for further analysis
        ridge_pred_path = os.path.join(tmp_dir, f"{symbol}_ridge_predictions.csv")
        pd.DataFrame({
            'Date': df_test['Date'].values,
            'Actual': y_test.values,
            'Ridge_Predicted': ridge_pred
        }).to_csv(ridge_pred_path, index=False)
        fs.put(ridge_pred_path, f"{bucket_name}/models/{symbol}_ridge_predictions.csv")
        
        print(f"Model saved with {test_size} test days and {val_size} validation days")
    except Exception as e:
        print(f"Error in train_model: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python train.py <symbol>")
        print("Example: python train.py AAPL")
        sys.exit(1)
    train_model(sys.argv[1])
