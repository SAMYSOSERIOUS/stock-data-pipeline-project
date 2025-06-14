import os
import yaml
from gcsfs import GCSFileSystem
import pandas as pd

def test_gcs_connection():
    print("Testing GCS connection...")
    
    # Set Google Cloud credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "c:/stock-data-pipeline-project/gcs-key.json"
    
    # Load config
    try:
        with open("c:/stock-data-pipeline-project/config.yaml") as f:
            config = yaml.safe_load(f)
        print("Config loaded successfully.")
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return
    
    # Access bucket
    bucket = config["gcs"]["bucket_name"]
    print(f"Bucket name: {bucket}")
    
    try:
        fs = GCSFileSystem()
        print("GCSFileSystem created successfully.")
    except Exception as e:
        print(f"Error creating GCSFileSystem: {str(e)}")
        return
    
    # Test if bucket exists
    try:
        bucket_exists = fs.exists(f"gs://{bucket}")
        print(f"Bucket exists: {bucket_exists}")
    except Exception as e:
        print(f"Error checking if bucket exists: {str(e)}")
        return
    
    # Test if symbols.csv exists
    try:
        symbols_exists = fs.exists(f"gs://{bucket}/symbols.csv")
        print(f"symbols.csv exists: {symbols_exists}")
        if symbols_exists:
            symbols = pd.read_csv(f"gs://{bucket}/symbols.csv")
            print(f"Number of symbols: {len(symbols)}")
            print(f"First 5 symbols: {symbols.head(5)}")
    except Exception as e:
        print(f"Error checking symbols.csv: {str(e)}")
    
    print("Test complete.")

if __name__ == "__main__":
    test_gcs_connection()
