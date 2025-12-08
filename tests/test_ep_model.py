import sys
import os
import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock xgboost BEFORE importing the model
sys.modules['xgboost'] = MagicMock()

from ml.expected_points import ExpectedPointsModel

def test_ep_model():
    print("Testing ExpectedPointsModel...")
    
    # 1. Initialize
    model = ExpectedPointsModel()
    print("  Initialization: PASS")
    
    # 2. Mock Training
    try:
        model.predict({'down': 1})
        print("  Untrained Catch: FAIL (Should raise error)")
    except ValueError:
        print("  Untrained Catch: PASS")
        
    # 3. Mock Data Structure
    mock_data = {
        'down': 1,
        'ydstogo': 10,
        'yardline_100': 75,
        'half_seconds_remaining': 1800,
        'posteam_timeouts_remaining': 3,
        'defteam_timeouts_remaining': 3,
        'score_differential': 0,
        'posteam': 'NE',
        'home_team': 'NE'
    }
    
    # Manually attach a mock model since we can't train
    model.model = MagicMock()
    model.model.predict.return_value = np.array([1.5]) 
    
    pred = model.predict(mock_data)
    print(f"  Prediction Result: {pred}")
    
    # Check if prediction is reasonable form (float or array)
    # Our mock returns array([1.5]), so predict([features])[0] -> 1.5
    assert isinstance(pred, (float, np.float32, np.float64)) or (isinstance(pred, np.ndarray) and pred.ndim==0), f"Prediction is {type(pred)}"
    
    print("  Inference Flow: PASS")

if __name__ == "__main__":
    test_ep_model()
