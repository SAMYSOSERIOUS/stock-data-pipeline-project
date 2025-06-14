import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from gcs_loader.load_symbols import load_symbols_from_gcs
from model.predict import predict

if __name__ == "__main__":
    symbols = load_symbols_from_gcs()
    print(f"Predicting for {len(symbols)} symbols...")
    for symbol in symbols:
        print(f"\n--- Predicting {symbol} ---")
        try:
            predict(symbol)
        except Exception as e:
            print(f"Error predicting {symbol}: {e}")
    print("\nAll predictions complete.")
