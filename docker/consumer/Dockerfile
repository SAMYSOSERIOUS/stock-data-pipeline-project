FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 --retries=10 -r requirements.txt

COPY my_kafka/consumer.py /app/consumer.py
COPY config.yaml /app/config.yaml

CMD ["python", "consumer.py"]
