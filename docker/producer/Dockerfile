FROM python:3.9

WORKDIR /app

# Copy global files from root of project
COPY requirements.txt .
COPY config.yaml .

# Copy source files from kafka and gcs_loader directories
COPY my_kafka/producer.py ./producer.py
COPY gcs-key.json .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the producer
CMD ["python", "producer.py"]
