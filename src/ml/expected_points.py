"""
Expected Points Model
Predicts Expected Points (EP) based on game state.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

class ExpectedPointsModel:
    def __init__(self):
        self.model = None
        self.feature_columns = [
            'down', 'ydstogo', 'yardline_100', 'half_seconds_remaining',
            'posteam_timeouts_remaining', 'defteam_timeouts_remaining',
            'score_differential', 'home_team'
        ]
        
    def prepare_data(self, df):
        # Basic cleaning and feature engineering
        df = df.copy()
        
        # Ensure numeric features
        for col in ['down', 'ydstogo', 'yardline_100', 'half_seconds_remaining', 
                   'posteam_timeouts_remaining', 'defteam_timeouts_remaining', 'score_differential']:
             if col in df.columns:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Handle home_team as binary (is_home_team) if needed, but for now specific team might not be useful 
        # without huge data. nflfastR often uses 'posteam_is_home'.
        # Let's check existing data or standard approach. 
        # Standard EP models often depend heavily on field position and down/dist.
        # We will assume 'home_team' column exists and might need encoding if it's a string, 
        # but for simple EP, 'posteam_type' (home/away) is better.
        # Let's simplify to standard features for now.
        
        # If 'home_team' is in columns, we might need to know if posteam == home_team
        if 'home_team' in df.columns and 'posteam' in df.columns:
            df['posteam_is_home'] = (df['posteam'] == df['home_team']).astype(int)
            if 'posteam_is_home' not in self.feature_columns:
                 self.feature_columns.append('posteam_is_home')
                 if 'home_team' in self.feature_columns:
                     self.feature_columns.remove('home_team')
        
        # Target: EP is usually calculated from next_score_type. 
        # If we are training, we need 'epa' or calculated points.
        # For this implementation, we assume the dataset has 'epa' or we predict it.
        # Or we predict 'expected_points' column if available.
        
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
        
        # We need a target. 'epa' is standard in nflverse data.
        if 'epa' not in df.columns:
             print("Warning: 'epa' column not found. Cannot train.")
             return
             
        df = df.dropna(subset=['epa'] + self.feature_columns)
        
        X = df[self.feature_columns]
        y = df['epa']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            random_state=42,
            n_jobs=-1
        )
        
        print("Training Expected Points Model...")
        self.model.fit(X_train, y_train)
        
        preds = self.model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)
        
        print(f"RMSE: {rmse:.4f}")
        print(f"R2: {r2:.4f}")
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'feature_columns': self.feature_columns
            }, save_path)
            print(f"Saved to {save_path}")
            
    def predict(self, features):
        if self.model is None:
             raise ValueError("Model not trained")
        
        if isinstance(features, dict):
            # Preprocessing for single prediction
            # logic to match training features
            if 'posteam' in features and 'home_team' in features:
                 features['posteam_is_home'] = 1 if features['posteam'] == features['home_team'] else 0
                 
            df = pd.DataFrame([features])
            # Ensure valid columns
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            
            X = df[self.feature_columns]
            return self.model.predict(X)[0]
            
        return self.model.predict(features)

    def load(self, path):
        data = joblib.load(path)
        self.model = data['model']
        self.feature_columns = data['feature_columns']
