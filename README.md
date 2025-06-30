# 📈 Stock Data Pipeline Project

A comprehensive real-time stock data pipeline built with Apache Kafka and Streamlit for data processing, analysis, and visualization.

## 🎯 Overview

This project implements a complete ETL pipeline for stock market data that:
- **Extracts** real-time stock data from multiple APIs
- **Transforms** and cleans the data using pandas
- **Loads** processed data into Google Cloud Storage and PostgreSQL
- **Visualizes** insights through an interactive Streamlit dashboard
- **Streams** real-time data using Apache Kafka

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐   
│   Data Sources  │    │   Apache Kafka  │    
│                 │    │                 │    
│ • Alpha Vantage │───▶│ • Stock Prices  │───┐
│ • Yahoo Finance │    │ • News Feeds    │   │
│ • News APIs     │    │ • Market Events │   │
└─────────────────┘    └─────────────────┘   │
                                            │
┌─────────────────┐    ┌─────────────────┐   │
│   Streamlit     │    │   Data Storage  │   │
│   Dashboard     │    │                 │   │
│                 │◀───│ • PostgreSQL    │◀──┘
│ • Real-time viz │    │ • Google Cloud  │
│ • Analytics     │    │   Storage       │
│ • Monitoring    │    │ • Local Files   │
└─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
Before running this project, ensure you have:
- Python 3.8+ installed
- Docker and Docker Compose installed
- Google Cloud Platform account with service account key
- API Keys for:
  - Alpha Vantage (free at alphavantage.co)
  - News API (free at newsapi.org)

### 1. Clone and Setup
```sh
git clone <your-repo-url>
cd stock-data-pipeline-project

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the environment template and edit your credentials:
```sh
cp .env.example .env
# Edit .env with your API keys and credentials
```

Required Environment Variables:
```
# API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_news_api_key

# Database
POSTGRES_USER=stockdb_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=stockdb

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=secrets/gcs-key.json
GCS_BUCKET_NAME=your-gcs-bucket
```

### 3. Google Cloud Setup
```sh
mkdir -p secrets
# Add your GCS service account key
type nul > secrets/gcs-key.json  # (or copy your key file here)
# Copy configuration file
cp config.yaml secrets/config.yaml
```

### 4. Start the Pipeline
```sh
docker-compose up -d
# Or start specific services
docker-compose up kafka zookeeper postgres -d
```

### 5. Access Applications
- Streamlit Dashboard: http://localhost:8501
- Kafka UI: http://localhost:9021 (if enabled)

## 📁 Project Structure

```
stock-data-pipeline-project/
├── data_collector/         # Data extraction modules
├── model/                  # Data models and transformations
├── gcs_uploader/           # Google Cloud Storage utilities
├── streamlit/              # Streamlit dashboard
├── my_kafka/               # Kafka producers and consumers
├── docker/                 # Docker configurations
├── docker-compose.yml      # Docker services configuration
├── requirements.txt        # Python dependencies
├── config.yaml             # Application configuration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🔧 Development Setup

### Local Development
```sh
pip install -r requirements-dev.txt
pre-commit install
python -m pytest tests/
streamlit run streamlit/app.py
# Start Kafka locally (optional)
cd my_kafka
python producer.py
```

### Database Setup
```sh
python scripts/init_db.py
python scripts/migrate.py
python scripts/seed_data.py
```

## 📊 Features
- **Real-time Data Pipeline**: Multi-source data ingestion from Alpha Vantage, Yahoo Finance, and news APIs. Apache Kafka for real-time data streaming. Automated data quality checks and error handling.
- **Data Storage & Processing**: PostgreSQL for structured data storage. Google Cloud Storage for data lake functionality. Pandas-based transformations for data cleaning and feature engineering. Configurable data retention policies.
- **Interactive Dashboard**: Real-time stock price monitoring with live updates. Technical analysis indicators (SMA, EMA, RSI, MACD). News sentiment analysis integrated with stock data. Portfolio tracking and performance analytics. Customizable alerts and notifications.
- **DevOps & Monitoring**: Docker containerization for easy deployment. Health checks and service monitoring. Centralized logging with structured logs. Environment-based configuration management.

## 🛠️ Configuration

### Main Configuration (`config.yaml`)
```yaml
# Data Sources
data_sources:
  alpha_vantage:
    base_url: "https://www.alphavantage.co/query"
    rate_limit: 5  # requests per minute
  news_api:
    base_url: "https://newsapi.org/v2"
    rate_limit: 100  # requests per day
# Database
database:
  host: "postgres"
  port: 5432
  name: "stockdb"
# Kafka
kafka:
  bootstrap_servers: ["kafka:9092"]
  topics:
    stock_prices: "stock-prices"
    news_feed: "news-feed"
# GCS
gcs:
  bucket_name: "your-stock-data-bucket"
  credentials_path: "secrets/gcs-key.json"
```

## 🧪 Testing
```sh
python -m pytest
# Run specific test categories
python -m pytest tests/unit/          # Unit tests
python -m pytest tests/integration/   # Integration tests
python -m pytest tests/e2e/           # End-to-end tests
# Run with coverage
python -m pytest --cov=src --cov-report=html
```

## 📈 Monitoring & Observability
- **Health Checks**: All services include health check endpoints (e.g., `curl http://localhost:8501/health` for Streamlit)
- **Logging**: Structured logging is configured for all components (`docker-compose logs -f streamlit`)
- **Metrics**: Data ingestion rates, processing latencies, error rates, data quality scores

## 🚀 Deployment

### Development Deployment
```sh
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

### Production Deployment
For production deployment, refer to the production checklist:
- Security: Update all default passwords and API keys
- SSL/TLS: Configure HTTPS with proper certificates
- Monitoring: Set up Prometheus and Grafana
- Backup: Configure automated database backups
- Scaling: Adjust resource limits and replica counts

## 🤝 Contributing
- Fork the repository
- Create a feature branch (`git checkout -b feature/amazing-feature`)
- Commit your changes (`git commit -m 'Add amazing feature'`)
- Push to the branch (`git push origin feature/amazing-feature`)
- Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use type hints where applicable

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
- Apache Software Foundation for Kafka
- Streamlit for the dashboard framework
- Alpha Vantage and Yahoo Finance for stock data APIs
- Google Cloud Platform for storage and compute services

Happy Trading! 📈💰
