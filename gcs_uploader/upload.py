import os
import yaml
from google.cloud import storage
import pandas as pd
import io
import json

def load_config():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def upload_df_to_gcs(df: pd.DataFrame, destination_blob_name: str, filetype='csv'):
    config = load_config()
    # Fix: use correct config keys for credentials and bucket
    gcp_credentials_path = config['gcs']['gcp_credentials_path']
    gcs_bucket = config['gcs']['bucket_name']
    client = storage.Client.from_service_account_json(gcp_credentials_path)
    bucket = client.get_bucket(gcs_bucket)
    blob = bucket.blob(destination_blob_name)

    if filetype == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        blob.upload_from_string(buffer.getvalue(), content_type='text/csv')
    elif filetype == 'json':
        json_str = df.to_json(orient='records')
        blob.upload_from_string(json_str, content_type='application/json')
    print(f"Uploaded {destination_blob_name} to GCS.")

def upload_json_to_gcs(data: dict, destination_blob_name: str):
    config = load_config()
    bucket_name = config["gcs"]["bucket_name"]

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(json.dumps(data), content_type='application/json')
    print(f"Uploaded {destination_blob_name} to GCS.")
