import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, mean_absolute_percentage_error
import matplotlib.pyplot as plt
import seaborn as sns
from gcsfs import GCSFileSystem
import yaml
import os
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Set GCS credentials environment variable
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(project_root, config["gcs"]["gcp_credentials_path"])

def plot_predictions_vs_actual(df, symbol, save_path):
    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], df['Actual'], label='Actual', alpha=0.7)
    plt.plot(df['Date'], df['Predicted'], label='Predicted', alpha=0.7)
    plt.title(f'{symbol} - Actual vs Predicted Stock Prices')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def plot_error_distribution(errors, symbol, save_path):
    plt.figure(figsize=(10, 6))
    sns.histplot(errors, bins=30, kde=True)
    plt.title(f'{symbol} - Prediction Error Distribution')
    plt.xlabel('Error')
    plt.ylabel('Frequency')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def evaluate(symbol):
    try:
        print(f"\n=== Evaluating Model Performance for {symbol} ===")
        
        # Initialize GCS filesystem with proper authentication
        fs = GCSFileSystem()
        bucket_name = config["gcs"]["bucket_name"]
        
        pred_path = f"{bucket_name}/predictions/{symbol}_predictions.csv"
        if not fs.exists(pred_path):
            print(f"No predictions found for {symbol}")
            return

        # Load predictions
        df = pd.read_csv(f"gs://{pred_path}")
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])

        # Calculate comprehensive metrics
        metrics = {
            "MSE": mean_squared_error(df["Actual"], df["Predicted"]),
            "RMSE": np.sqrt(mean_squared_error(df["Actual"], df["Predicted"])),
            "MAE": mean_absolute_error(df["Actual"], df["Predicted"]),
            "MAPE": mean_absolute_percentage_error(df["Actual"], df["Predicted"]) * 100,
            "R2": r2_score(df["Actual"], df["Predicted"]),
            "Direction_Accuracy": (np.sign(df["Direction_Actual"]) == np.sign(df["Direction_Predicted"])).mean() * 100
        }

        # Print detailed evaluation results
        print("\n=== Model Performance Metrics ===")
        print(f"Mean Squared Error (MSE): {metrics['MSE']:.4f}")
        print(f"Root Mean Squared Error (RMSE): {metrics['RMSE']:.4f}")
        print(f"Mean Absolute Error (MAE): {metrics['MAE']:.4f}")
        print(f"Mean Absolute Percentage Error (MAPE): {metrics['MAPE']:.2f}%")
        print(f"R-squared (R2) Score: {metrics['R2']:.4f}")
        print(f"Direction Accuracy: {metrics['Direction_Accuracy']:.2f}%")

        # Calculate additional trading-specific metrics
        df['Daily_Return'] = df['Actual'].pct_change()
        df['Predicted_Return'] = df['Predicted'].pct_change()
        
        # Trading simulation metrics (assuming simple strategy based on predicted direction)
        correct_directions = (df['Direction_Actual'] == df['Direction_Predicted']).sum()
        total_predictions = len(df['Direction_Actual'].dropna())
        
        print("\n=== Trading Performance Metrics ===")
        print(f"Correct Direction Predictions: {correct_directions} out of {total_predictions}")
        print(f"Direction Accuracy: {(correct_directions/total_predictions)*100:.2f}%")

        # Ensure /tmp directory exists
        tmp_dir = os.path.join(os.path.abspath(os.sep), 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        # Generate and save visualizations
        print("\nGenerating visualizations...")
        
        # Plot predictions vs actual
        pred_plot_path = os.path.join(tmp_dir, f"{symbol}_pred_vs_actual.png")
        plot_predictions_vs_actual(df, symbol, pred_plot_path)
        
        # Plot error distribution
        error_plot_path = os.path.join(tmp_dir, f"{symbol}_error_dist.png")
        plot_error_distribution(df['Error'], symbol, error_plot_path)

        # Save updated metrics and plots to GCS
        print("\nSaving evaluation results...")
        
        # Save metrics
        metrics_df = pd.DataFrame([metrics])
        metrics_path = os.path.join(tmp_dir, f"{symbol}_evaluation.csv")
        metrics_df.to_csv(metrics_path, index=False)
        
        # Upload to GCS
        fs.put(metrics_path, f"{bucket_name}/evaluation/{symbol}_evaluation.csv")
        fs.put(pred_plot_path, f"{bucket_name}/evaluation/{symbol}_pred_vs_actual.png")
        fs.put(error_plot_path, f"{bucket_name}/evaluation/{symbol}_error_dist.png")
        
        print(f"\nAll evaluation results saved to GCS bucket: {bucket_name}")
        print("├── evaluation/")
        print(f"│   ├── {symbol}_evaluation.csv")
        print(f"│   ├── {symbol}_pred_vs_actual.png")
        print(f"│   └── {symbol}_error_dist.png")

    except Exception as e:
        print(f"\nError in evaluate: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python evaluate.py <symbol>")
        print("Example: python evaluate.py AAPL")
        sys.exit(1)
    evaluate(sys.argv[1])
