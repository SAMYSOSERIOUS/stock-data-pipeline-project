import os
import sys

# Add project root to Python path - move this before other imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import json
import yaml
from datetime import datetime
from json import JSONEncoder
import pandas as pd
from data_collector.fetch_data import fetch_stock_data
from gcs_loader.load_symbols import load_symbols_from_gcs
from gcs_uploader.upload import upload_df_to_gcs
from kafka import KafkaProducer
import time
from google.cloud import storage
from google.oauth2 import service_account

def load_config():
    config_path = os.path.join(project_root, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        return super().default(obj)

def send_to_kafka(producer, topic, symbol, info_df, hist_df):
    try:
        # Create message payload
        message = {
            'symbol': symbol,
            'info': info_df.to_dict(orient='records')[0],
            'history': hist_df.to_dict(orient='records')
        }
        # Send to Kafka and get future
        future = producer.send(topic, value=message, key=symbol.encode('utf-8'))
        # Wait for the message to be delivered
        future.get(timeout=10)
    except Exception as e:
        print(f"Error sending {symbol} to Kafka: {str(e)}")
        raise

def upload_to_gcs(symbol, info_df, hist_df, config):
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config['gcs']['gcp_credentials_path']
        info_path = f"{config['gcs']['data_prefix']}{symbol}_info.csv"
        hist_path = f"{config['gcs']['data_prefix']}{symbol}_hist.csv"
        
        upload_df_to_gcs(info_df, info_path)
        upload_df_to_gcs(hist_df, hist_path)
        
        if not verify_gcs_upload(config['gcs']['bucket_name'], info_path) or \
           not verify_gcs_upload(config['gcs']['bucket_name'], hist_path):
            raise Exception(f"Failed to verify {symbol} files in GCS")
            
        return True
    except Exception as e:
        print(f"Error uploading {symbol} to GCS: {str(e)}")
        return False

def verify_gcs_upload(bucket_name, blob_name):
    """Verify file exists in GCS"""
    config = load_config()
    # Set credentials via environment variable for compatibility
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config['gcs']['gcp_credentials_path']
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.exists()

def verify_kafka_message(producer, topic, message_key):
    """Verify message was sent to Kafka"""
    future = producer.send(topic, key=message_key)
    try:
        record_metadata = future.get(timeout=10)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    config = load_config()
    
    # Add retry logic for Kafka connection
    retries = 3
    while retries > 0:
        try:
            producer = KafkaProducer(
                bootstrap_servers=config['kafka']['bootstrap_servers'].split(','),
                api_version=(2, 8, 1),
                request_timeout_ms=60000,
                retry_backoff_ms=2000,
                max_block_ms=60000,
                security_protocol="PLAINTEXT",
                value_serializer=lambda x: json.dumps(x, cls=CustomJSONEncoder).encode('utf-8'),
                reconnect_backoff_ms=5000,
                reconnect_backoff_max_ms=10000
            )
            producer.bootstrap_connected()
            print("✓ Connected to Kafka")
            break
        except Exception as e:
            retries -= 1
            if retries == 0:
                print("Error: Failed to connect to Kafka - please ensure Kafka is running")
                raise
            time.sleep(5)
    
    try:
        symbols = load_symbols_from_gcs()
        total = len(symbols)
        print(f"Processing {total} symbols...")
        
        for i, symbol in enumerate(symbols, 1):
            try:
                print(f"\r[{i}/{total}] Processing {symbol}...", end="", flush=True)
                
                info_df, hist_df = fetch_stock_data(symbol)
                if not upload_to_gcs(symbol, info_df, hist_df, config):
                    continue
                
                send_to_kafka(producer, config["kafka"]["topic_name"], symbol, info_df, hist_df)
                producer.flush()
                
            except Exception as e:
                print(f"\nError with {symbol}: {str(e)}")
                continue
            
            time.sleep(1)  # Rate limiting
        print("\nCompleted processing all symbols")
    
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise
    finally:
        producer.flush()
        producer.close()
