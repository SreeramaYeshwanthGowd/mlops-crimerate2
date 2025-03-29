# Real-Time Crime Data Analytics and Anomaly Detection

This project implements a complete MLOps pipeline for real-time crime data analytics and anomaly detection using various open-source crime data APIs.

## Project Structure
- `data_ingestion/`: Kafka producer for crime data APIs
- `data_processing/`: Spark streaming jobs
- `model/`: Anomaly detection model training and deployment
- `dashboard/`: Plotly Dash interactive dashboard
- `chatbot/`: Rasa chatbot implementation
- `docker/`: Docker and Docker Compose files
- `monitoring/`: Prometheus and Grafana configuration
- `docs/`: Project documentation

## Implementation Plan
1. Set up data ingestion with crime data APIs and Kafka
2. Implement data processing with Spark Streaming and Delta Lake
3. Train anomaly detection model with MLflow
4. Deploy model as API with FastAPI
5. Create interactive dashboard with Plotly Dash
6. Integrate Rasa chatbot
7. Containerize components with Docker
8. Set up CI/CD and monitoring
9. Deploy dashboard to Hugging Face Spaces
10. Deploy chatbot to Heroku
