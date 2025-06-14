import os
import yaml
import pandas as pd
from google.cloud import storage
import tempfile

def load_config():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def load_symbols_from_gcs():
    """Load symbols from GCS bucket"""
    try:
        config = load_config()
        # Set credentials via environment variable for compatibility
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config['gcs']['gcp_credentials_path']
        client = storage.Client()
        bucket = client.get_bucket(config['gcs']['bucket_name'])
        blob = bucket.blob(config['symbols_file'])
        # Use a cross-platform temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            tmp_path = tmp_file.name
        blob.download_to_filename(tmp_path)
        symbols_df = pd.read_csv(tmp_path)
        os.remove(tmp_path)
        return symbols_df['symbol'].tolist()
    except Exception as e:
        print(f"Error loading symbols from GCS: {str(e)}")
        raise

if __name__ == "__main__":
    symbols = load_symbols_from_gcs()
    print(f"Loaded {len(symbols)} symbols")

