import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

# Add src to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock xgboost BEFORE importing the model
sys.modules['xgboost'] = MagicMock()

from ml.scoring_probability import ScoringProbabilityModel

def test_scoring_prob_model():
    print("Testing ScoringProbabilityModel...")
    
    model = ScoringProbabilityModel()
    print("  Initialization: PASS")
    
    class MockXGBClassifier:
        def predict_proba(self, X):
            # 7 classes, sum to 1
            n = len(X)
            # return shape (n, 7)
            return np.array([[0.1, 0.1, 0.1, 0.1, 0.2, 0.2, 0.2]] * n)
            
        @property
        def classes_(self):
            return ['No_Score', 'Opp_FG', 'Opp_Safety', 'Opp_TD', 'FG', 'Safety', 'TD']

    model.model = MockXGBClassifier()
    
    mock_data = {
        'down': 3,
        'ydstogo': 5,
        'yardline_100': 20, # Redzone
        'half_seconds_remaining': 300,
        'posteam_timeouts_remaining': 2,
        'defteam_timeouts_remaining': 2,
        'score_differential': -4,
        'posteam': 'KC',
        'home_team': 'KC'
    }
    
    probs = model.predict_proba(mock_data)
    print("  Probabilities:", probs)
    print(f"  Sum: {sum(probs):.4f}")
    
    assert len(probs) == 7, "Output should have 7 classes"
    assert abs(sum(probs) - 1.0) < 0.001, "Probabilities should sum to 1"
    
    print("  Inference Flow: PASS")

if __name__ == "__main__":
    test_scoring_prob_model()
