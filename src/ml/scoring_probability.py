"""
Scoring Probability Model
Predicts probability of next score type: TD, FG, Safety, No Score
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, accuracy_score

class ScoringProbabilityModel:
    def __init__(self):
        self.model = None
        self.feature_columns = [
            'down', 'ydstogo', 'yardline_100', 'half_seconds_remaining',
            'posteam_timeouts_remaining', 'defteam_timeouts_remaining',
            'score_differential', 'posteam_is_home'
        ]
        self.classes = ['No_Score', 'Opp_FG', 'Opp_Safety', 'Opp_TD', 'FG', 'Safety', 'TD']
        # Simplified classes often used: Touchdown, Field Goal, Safety, No Score (for each team)
        # 7 classes usually: TD, FG, Safety, No Score, Opp_TD, Opp_FG, Opp_Safety
        
    def prepare_data(self, df):
        df = df.copy()
        
        if 'home_team' in df.columns and 'posteam' in df.columns:
            df['posteam_is_home'] = (df['posteam'] == df['home_team']).astype(int)
        else:
             if 'posteam_is_home' not in df.columns:
                 df['posteam_is_home'] = 0 # Default if unknown
                 
        for col in self.feature_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df

    def train(self, data_paths, save_path=None):
        if isinstance(data_paths, str):
            data_paths = [data_paths]
            
        dfs = []
        for path in data_paths:
            print(f"Loading {path}...")
            df = pd.read_csv(path, low_memory=False)
            dfs.append(df)
            
        df = pd.concat(dfs, ignore_index=True)
        df = self.prepare_data(df)
        
        # Need 'next_score_type' or similar label. 
        # In nflverse data, this is often derived or explicit.
        # Assuming column 'next_score_type' exists or we need to derive it.
        # For this template, we assume it exists.
        if 'next_score_type' not in df.columns:
            # Fallback for demonstration if strictly following plan without full data inspection
            print("Warning: 'next_score_type' not found. Cannot train.")
            return

        df = df.dropna(subset=['next_score_type'] + self.feature_columns)
        
        X = df[self.feature_columns]
        y = df['next_score_type'] # Should be categorical
        
        # Map classes if needed to integer 0-6
        # ... implementation detail ...
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            objective='multi:softprob',
            num_class=7, 
            random_state=42,
            n_jobs=-1
        )
        
        print("Training Scoring Probability Model...")
        self.model.fit(X_train, y_train)
        
        preds = self.model.predict(X_test)
        probs = self.model.predict_proba(X_test)
        
        acc = accuracy_score(y_test, preds)
        loss = log_loss(y_test, probs)
        
        print(f"Accuracy: {acc:.4f}")
        print(f"Log Loss: {loss:.4f}")
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'feature_columns': self.feature_columns,
                'classes': self.model.classes_
            }, save_path)
            print(f"Saved to {save_path}")

    def predict_proba(self, features):
        if self.model is None:
            raise ValueError("Model not trained")
            
        if isinstance(features, dict):
            if 'posteam' in features and 'home_team' in features:
                 features['posteam_is_home'] = 1 if features['posteam'] == features['home_team'] else 0
            
            df = pd.DataFrame([features])
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            X = df[self.feature_columns]
            return self.model.predict_proba(X)[0]
            
        return self.model.predict_proba(features)

    def load(self, path):
        data = joblib.load(path)
        self.model = data['model']
        self.feature_columns = data['feature_columns']
