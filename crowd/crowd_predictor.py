# crowd/crowd_predictor.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

class CrowdPredictor:
    """
    Predict crowd behavior and occupancy.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.models = {}
        self.scalers = {}
        self.historical_data = defaultdict(list)
        self.is_trained = False
        
        # Prediction parameters
        self.prediction_horizon = self.config.get('prediction_horizon', 30)  # minutes
        self.min_training_samples = self.config.get('min_training_samples', 100)
        
    def train_model(self, camera_id: int, 
                    training_data: List[Dict]):
        """
        Train prediction model for a camera.
        """
        if len(training_data) < self.min_training_samples:
            print(f"⚠️ Not enough training data for camera {camera_id}: "
                  f"{len(training_data)} < {self.min_training_samples}")
            return
        
        # Prepare features
        X = []
        y = []
        
        for data_point in training_data:
            features = self._extract_features(data_point)
            X.append(features)
            y.append(data_point['occupancy'])
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train model
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_scaled, y)
        
        # Store model
        self.models[camera_id] = model
        self.scalers[camera_id] = scaler
        
        print(f"✅ Trained model for camera {camera_id} on {len(X)} samples")
        self.is_trained = True
    
    def predict_occupancy(self, camera_id: int, 
                          features: Dict) -> Dict:
        """
        Predict future occupancy for a camera.
        """
        if camera_id not in self.models:
            return {
                'prediction': 0,
                'confidence': 0,
                'error': 0,
                'message': 'No model trained for this camera'
            }
        
        # Extract features
        X = np.array([self._extract_features(features)])
        
        # Scale features
        X_scaled = self.scalers[camera_id].transform(X)
        
        # Predict
        prediction = self.models[camera_id].predict(X_scaled)[0]
        
        # Estimate confidence (using model's prediction error)
        # Use prediction intervals from forest
        predictions = [tree.predict(X_scaled)[0] for tree in self.models[camera_id].estimators_]
        std = np.std(predictions)
        confidence = 1 - (std / (prediction + 1))  # Normalize confidence
        
        # Get feature importance
        if hasattr(self.models[camera_id], 'feature_importances_'):
            importance = self.models[camera_id].feature_importances_.tolist()
        else:
            importance = None
        
        return {
            'prediction': float(prediction),
            'confidence': float(max(0, min(1, confidence))),
            'std_dev': float(std),
            'feature_importance': importance,
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_features(self, data: Dict) -> List[float]:
        """
        Extract features for prediction.
        """
        features = []
        
        # Temporal features
        timestamp = data.get('timestamp')
        if timestamp:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Hour (sin/cos for circular)
            hour = timestamp.hour
            features.append(np.sin(2 * np.pi * hour / 24))
            features.append(np.cos(2 * np.pi * hour / 24))
            
            # Day of week (sin/cos for circular)
            day = timestamp.weekday()
            features.append(np.sin(2 * np.pi * day / 7))
            features.append(np.cos(2 * np.pi * day / 7))
        
        # Current occupancy
        features.append(data.get('occupancy', 0))
        
        # Rate of change
        features.append(data.get('entry_rate', 0))
        features.append(data.get('exit_rate', 0))
        
        # Historical averages
        features.append(data.get('avg_occupancy_hour', 0))
        features.append(data.get('avg_occupancy_day', 0))
        
        # Weather (if available)
        features.append(data.get('temperature', 20))
        features.append(data.get('precipitation', 0))
        
        # Special events
        features.append(data.get('is_weekend', 0))
        features.append(data.get('is_holiday', 0))
        
        return features
    
    def get_trend_forecast(self, camera_id: int, 
                           hours: int = 24) -> List[Dict]:
        """
        Get trend forecast for the next N hours.
        """
        forecasts = []
        current_time = datetime.now()
        
        for hour in range(hours):
            future_time = current_time + timedelta(hours=hour)
            
            features = {
                'timestamp': future_time,
                'occupancy': self._get_historical_avg(camera_id, future_time),
                'entry_rate': 0,
                'exit_rate': 0,
                'avg_occupancy_hour': self._get_hourly_avg(camera_id, future_time.hour),
                'avg_occupancy_day': self._get_daily_avg(camera_id, future_time.weekday()),
                'temperature': 20,
                'precipitation': 0,
                'is_weekend': 1 if future_time.weekday() >= 5 else 0,
                'is_holiday': 0
            }
            
            prediction = self.predict_occupancy(camera_id, features)
            
            forecasts.append({
                'timestamp': future_time.isoformat(),
                'predicted_occupancy': prediction['prediction'],
                'confidence': prediction['confidence']
            })
        
        return forecasts
    
    def _get_historical_avg(self, camera_id: int, 
                           timestamp: datetime) -> float:
        """Get historical average occupancy for a time."""
        # Simplified: use stored historical data
        if camera_id not in self.historical_data:
            return 0
        
        # Find data points in the same hour
        same_hour = []
        for data in self.historical_data[camera_id]:
            if data['timestamp'].hour == timestamp.hour:
                same_hour.append(data['occupancy'])
        
        return np.mean(same_hour) if same_hour else 0
    
    def _get_hourly_avg(self, camera_id: int, hour: int) -> float:
        """Get average occupancy for an hour."""
        if camera_id not in self.historical_data:
            return 0
        
        same_hour = []
        for data in self.historical_data[camera_id]:
            if data['timestamp'].hour == hour:
                same_hour.append(data['occupancy'])
        
        return np.mean(same_hour) if same_hour else 0
    
    def _get_daily_avg(self, camera_id: int, day: int) -> float:
        """Get average occupancy for a day of week."""
        if camera_id not in self.historical_data:
            return 0
        
        same_day = []
        for data in self.historical_data[camera_id]:
            if data['timestamp'].weekday() == day:
                same_day.append(data['occupancy'])
        
        return np.mean(same_day) if same_day else 0