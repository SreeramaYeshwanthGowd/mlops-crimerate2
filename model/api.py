from fastapi import FastAPI, HTTPException, Request
import mlflow.pyfunc
import pandas as pd
import numpy as np
import json
import os
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Define request model
class PredictionRequest(BaseModel):
    location_name: str
    crime_type: str
    incident_count: int
    additional_features: Optional[Dict[str, float]] = None

# Define response model
class PredictionResponse(BaseModel):
    location_name: str
    crime_type: str
    anomaly_score: float
    is_anomaly: bool

# Initialize FastAPI app
app = FastAPI(
    title="Crime Anomaly Detection API",
    description="API for detecting anomalies in crime data",
    version="1.0.0"
)

# Load the model
@app.on_event("startup")
async def startup_event():
    global model, scaler
    
    # Set MLflow tracking URI
    mlflow.set_tracking_uri("http://localhost:5000")
    
    # Load the latest model version
    try:
        model = mlflow.pyfunc.load_model("models:/CrimeAnomalyDetector/latest")
        scaler = mlflow.pyfunc.load_model("runs:/<RUN_ID>/scaler")
        print("Model and scaler loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        # Load from local path if MLflow server is not available
        model_path = os.getenv("MODEL_PATH", "/home/ubuntu/mlops-crimerate-project/model/models/crime_anomaly_model")
        scaler_path = os.getenv("SCALER_PATH", "/home/ubuntu/mlops-crimerate-project/model/models/scaler")
        model = mlflow.pyfunc.load_model(model_path)
        scaler = mlflow.pyfunc.load_model(scaler_path)

@app.get("/")
def read_root():
    return {"message": "Crime Anomaly Detection API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    try:
        # Create a feature dictionary
        features = {
            'incident_count': request.incident_count,
            f'location_{request.location_name}': 1,
            f'crime_{request.crime_type}': 1
        }
        
        # Add any additional features
        if request.additional_features:
            features.update(request.additional_features)
        
        # Convert to DataFrame
        df = pd.DataFrame([features])
        
        # Fill missing columns with 0 (for one-hot encoded features not in the request)
        # This is a simplified approach - in production, you'd need to ensure all expected columns are present
        
        # Scale features
        scaled_features = scaler.predict(df)
        
        # Make prediction
        anomaly_score = model.predict(scaled_features)[0]
        is_anomaly = anomaly_score < 0  # Isolation Forest: -1 for anomalies, 1 for normal
        
        # Convert anomaly score to a more interpretable value (0 to 1, where 1 is most anomalous)
        normalized_score = (1 - (anomaly_score + 1) / 2)
        
        return {
            "location_name": request.location_name,
            "crime_type": request.crime_type,
            "anomaly_score": float(normalized_score),
            "is_anomaly": bool(is_anomaly)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

@app.post("/batch-predict")
async def batch_predict(request: List[PredictionRequest]):
    try:
        results = []
        for item in request:
            # Process each item
            prediction = await predict(item)
            results.append(prediction)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
