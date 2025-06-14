# 📈 Stock Data Pipeline Project

A comprehensive real-time stock data pipeline built with Apache Kafka, Apache , and Streamlit for data processing, analysis, and visualization.

## 🎯 Overview

This project implements a complete ETL pipeline for stock market data that:
- **Extracts** real-time stock data from multiple APIs
- **Transforms** and cleans the data using pandas and
- **Loads** processed data into Google Cloud Storage and PostgreSQL
- **Visualizes** insights through an interactive Streamlit dashboard
- **Streams** real-time data using Apache Kafka

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐   
│   Data Sources  │    │   Apache Kafka  │    
│                 │    │                 │    
│ • Alpha Vantage │───▶│ • Stock Prices │───-----------|
│ • Yahoo Finance │    │ • News Feeds    │              |
│ • News APIs     │    │ • Market Events │              |
└─────────────────┘    └─────────────────┘              |
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│   Streamlit     │    │   Data Storage  │              │
│   Dashboard     │    │                 │              │
│                 │◀───│ • PostgreSQL    │◀────────────┘
│ • Real-time viz │    │ • Google Cloud  │
│ • Analytics     │    │   Storage       │
│ • Monitoring    │    │ • Local Files   │
└─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

Before running this project, ensure you have:

- **Python 3.8+** installed
- **Docker** and **Docker Compose** installed
- **Google Cloud Platform** account with service account key
- **API Keys** for:
  - Alpha Vantage (free at [alphavantage.co](https://www.alphavantage.co/support/#api-key))
  - News API (free at [newsapi.org](https://newsapi.org/register))

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd stock-data-pipeline-project

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your credentials
nano .env
```

**Required Environment Variables:**
```env
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

```bash
# Create secrets directory
mkdir -p secrets

# Add your GCS service account key
cp /path/to/your/gcs-key.json secrets/gcs-key.json

# Copy configuration file
cp config.yaml secrets/config.yaml
```

### 4. Start the Pipeline

```bash
# Start all services with Docker Compose
docker-compose up -d

# Or start specific services
docker-compose up kafka zookeeper postgres -d
```

### 5. Access Applications

- **Streamlit Dashboard**: http://localhost:8501
- ** Web UI**: http://localhost:8080
- **Kafka UI**: http://localhost:9021 (if enabled)

## 📁 Project Structure

```
stock-data-pipeline-project/
├── 📁 /                 # Apache  DAGs and plugins
│   ├── dags/
│   │   ├── stock_data_dag.py   # Main ETL pipeline DAG
│   │   └── news_data_dag.py    # News data collection DAG
│   └── plugins/
├── 📁 data_collector/          # Data extraction modules
│   ├── __init__.py
│   ├── alpha_vantage.py        # Alpha Vantage API client
│   ├── yahoo_finance.py        # Yahoo Finance API client
│   └── news_collector.py       # News data collector
├── 📁 model/                   # Data models and transformations
│   ├── __init__.py
│   ├── stock_model.py          # Stock data models
│   └── transformations.py      # Data transformation functions
├── 📁 gcs_uploader/           # Google Cloud Storage utilities
│   ├── __init__.py
│   └── uploader.py            # GCS upload functions
├── 📁 streamlit/              # Streamlit dashboard
│   ├── app.py                 # Main dashboard app
│   ├── pages/                 # Multi-page dashboard
│   └── components/            # Reusable UI components
├── 📁 my_kafka/               # Kafka producers and consumers
│   ├── __init__.py
│   ├── producer.py            # Kafka data producer
│   └── consumer.py            # Kafka data consumer
├── 📁 docker/                 # Docker configurations
│   └── /               #  Docker setup
├── 📄 docker-compose.yml      # Docker services configuration
├── 📄 requirements.txt        # Python dependencies
├── 📄 config.yaml            # Application configuration
├── 📄 .env.example           # Environment variables template
└── 📄 README.md              # This file
```

## 🔧 Development Setup

### Local Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Run tests
python -m pytest tests/

# Start Streamlit for development
streamlit run streamlit/app.py

# Start Kafka locally (optional)
cd my_kafka
python producer.py
```

### Database Setup

```bash
# Initialize PostgreSQL database
python scripts/init_db.py

# Run migrations
python scripts/migrate.py

# Seed with sample data
python scripts/seed_data.py
```

## 📊 Features

### Real-time Data Pipeline
- **Multi-source data ingestion** from Alpha Vantage, Yahoo Finance, and news APIs
- **Apache Kafka** for real-time data streaming
- **Apache ** for workflow orchestration and scheduling
- **Automated data quality checks** and error handling

### Data Storage & Processing
- **PostgreSQL** for structured data storage
- **Google Cloud Storage** for data lake functionality
- **Pandas-based transformations** for data cleaning and feature engineering
- **Configurable data retention** policies

### Interactive Dashboard
- **Real-time stock price monitoring** with live updates
- **Technical analysis indicators** (SMA, EMA, RSI, MACD)
- **News sentiment analysis** integrated with stock data
- **Portfolio tracking** and performance analytics
- **Customizable alerts** and notifications

### DevOps & Monitoring
- **Docker containerization** for easy deployment
- **Health checks** and service monitoring
- **Centralized logging** with structured logs
- **Environment-based configuration** management

## 🛠️ Configuration

### Main Configuration (config.yaml)

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

###  DAGs Configuration

The project includes several pre-configured DAGs:

- **`stock_data_dag.py`**: Main ETL pipeline (runs every 15 minutes)
- **`news_data_dag.py`**: News data collection (runs hourly)
- **`data_quality_dag.py`**: Data quality checks (runs daily)

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/          # Unit tests
python -m pytest tests/integration/   # Integration tests
python -m pytest tests/e2e/          # End-to-end tests

# Run with coverage
python -m pytest --cov=src --cov-report=html
```

## 📈 Monitoring & Observability

### Health Checks

All services include health check endpoints:

```bash
# Check service health
curl http://localhost:8501/health      # Streamlit
curl http://localhost:8080/health      # 
```

### Logging

Structured logging is configured for all components:

```bash
# View logs
docker-compose logs -f streamlit
docker-compose logs -f -webserver
```

### Metrics

Key metrics are tracked:
- Data ingestion rates
- Processing latencies  
- Error rates
- Data quality scores

## 🚀 Deployment

### Development Deployment

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Production Deployment

For production deployment, refer to the production checklist:

1. **Security**: Update all default passwords and API keys
2. **SSL/TLS**: Configure HTTPS with proper certificates  
3. **Monitoring**: Set up Prometheus and Grafana
4. **Backup**: Configure automated database backups
5. **Scaling**: Adjust resource limits and replica counts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use type hints where applicable

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Apache Software Foundation** for Kafka and 
- **Streamlit** for the amazing dashboard framework
- **Alpha Vantage** and **Yahoo Finance** for stock data APIs
- **Google Cloud Platform** for storage and compute services



**Happy Trading! 📈💰**
