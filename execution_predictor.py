from decimal import Decimal
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from datetime import datetime
import logging
import os
from config import settings
from typing import List, Dict, Union, Any

class ExecutionPredictor:
    def __init__(self):
        self.model = self._load_model()
        self.features = {
            'latency': [],
            'volume': [],
            'spread': [],
            'timestamp': []
        }
        self.exchange_latency = {}

    def _load_model(self) -> GradientBoostingRegressor:
        """Load the ML model or create a default one if loading fails"""
        try:
            # Check if model file exists
            if os.path.exists(settings.ML_MODEL_PATH):
                return joblib.load(settings.ML_MODEL_PATH)
            else:
                logging.warning(f"Model file {settings.ML_MODEL_PATH} not found, using default model")
                return self._create_default_model()
        except Exception as e:
            logging.warning(f"Error loading model: {e}. Using default model.")