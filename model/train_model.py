import os
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from delta.tables import DeltaTable
from pyspark.sql import SparkSession

# Create Spark session
def create_spark_session():
    return (SparkSession.builder
            .appName("CrimeModelTraining")
            .config("spark.jars.packages", "io.delta:delta-core_2.12:1.0.0")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .getOrCreate())

# Load data from Delta Lake
def load_data_from_delta(spark, delta_path):
    delta_table = DeltaTable.forPath(spark, delta_path)
    return delta_table.toDF()

# Prepare features for anomaly detection
def prepare_features(df):
    # Convert Spark DataFrame to Pandas
    pandas_df = df.toPandas()
    
    # Extract relevant features
    features = pandas_df[['incident_count']]
    
    # Add location and crime type as one-hot encoded features
    location_dummies = pd.get_dummies(pandas_df['location_name'], prefix='location')
    crime_dummies = pd.get_dummies(pandas_df['crime_type'], prefix='crime')
    
    # Combine features
    features = pd.concat([features, location_dummies, crime_dummies], axis=1)
    
    # Handle missing values
    features = features.fillna(0)
    
    return features

# Train anomaly detection model
def train_anomaly_detection_model(X_train, contamination=0.05):
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Train Isolation Forest model
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42
    )
    model.fit(X_train_scaled)
    
    return model, scaler

def main():
    # Set MLflow tracking URI
    mlflow.set_tracking_uri("http://localhost:5000")
    
    # Create experiment
    mlflow_experiment = "crime_anomaly_detection"
    mlflow.set_experiment(mlflow_experiment)
    
    # Create Spark session
    spark = create_spark_session()
    
    # Load aggregated crime data from Delta Lake
    delta_path = "/home/ubuntu/mlops-crimerate-project/data/delta/aggregated"
    crime_df = load_data_from_delta(spark, delta_path)
    
    # Prepare features
    features = prepare_features(crime_df)
    
    # Start MLflow run
    with mlflow.start_run(run_name="isolation_forest_model"):
        # Log parameters
        mlflow.log_param("model_type", "IsolationForest")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("contamination", 0.05)
        
        # Train model
        model, scaler = train_anomaly_detection_model(features)
        
        # Make predictions on training data to evaluate
        predictions = model.predict(scaler.transform(features))
        anomaly_score = model.decision_function(scaler.transform(features))
        
        # Calculate metrics
        n_anomalies = sum(predictions == -1)
        anomaly_ratio = n_anomalies / len(predictions)
        
        # Log metrics
        mlflow.log_metric("n_anomalies", n_anomalies)
        mlflow.log_metric("anomaly_ratio", anomaly_ratio)
        
        # Log model with preprocessing pipeline
        mlflow.sklearn.log_model(
            model,
            "crime_anomaly_model",
            registered_model_name="CrimeAnomalyDetector"
        )
        
        # Log scaler as artifact
        mlflow.sklearn.log_model(
            scaler,
            "scaler"
        )
        
        print(f"Model trained and logged to MLflow with run_id: {mlflow.active_run().info.run_id}")

if __name__ == "__main__":
    main()
