from kafka import KafkaConsumer
import json
import yaml
import os

def load_config():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.yaml")
    print(f"Loading config from: {config_path}")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        print(f"Loaded config: {config}")
        return config

def check_messages(consumer, timeout_ms=5000):
    """
    Check if there are any messages in the Kafka topic
    Returns: tuple (has_messages: bool, message_count: int)
    """
    messages = consumer.poll(timeout_ms=timeout_ms)
    message_count = sum(len(msgs) for msgs in messages.values())
    return bool(message_count), message_count

if __name__ == "__main__":
    config = load_config()
    consumer = KafkaConsumer(
        config["kafka"]["topic_name"],
        bootstrap_servers=config["kafka"]["bootstrap_servers"],
        auto_offset_reset='earliest',
        group_id='stock-consumer-group',
        enable_auto_commit=True
    )

    # Check for messages first
    has_messages, count = check_messages(consumer)
    if not has_messages:
        print("No messages found in topic")
    else:
        print(f"Found {count} messages. Processing...")

    # Process messages
    for msg in consumer:
        if msg.value is None:
            print("Warning: Received message with no value. Skipping.")
            continue
        try:
            data = json.loads(msg.value.decode('utf-8'))
        except Exception as e:
            print(f"Warning: Could not decode message value as JSON: {e}. Skipping.")
            continue
        if not isinstance(data, dict) or 'symbol' not in data:
            print(f"Warning: Unexpected message format: {data}. Skipping.")
            continue
        print(f"\nReceived data for {data['symbol']}")
        print(f"Info keys: {list(data['info'].keys())[:5]}...")
        print(f"History sample: {data['history'][:1]}")
        print("Full message:")
        print(json.dumps(data, indent=2))
