import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from gcs_loader.load_symbols import load_symbols_from_gcs
from model.evaluate import evaluate

def main():
    symbols = load_symbols_from_gcs()
    print(f"Evaluating for {len(symbols)} symbols...")
    any_error = False
    for symbol in symbols:
        print(f"\n--- Evaluating {symbol} ---")
        try:
            evaluate(symbol)
        except Exception as e:
            print(f"Error evaluating {symbol}: {e}")
            any_error = True
        sys.stdout.flush()
    print("\nAll evaluations complete.")
    if any_error:
        sys.exit(1)

if __name__ == "__main__":
    main()
