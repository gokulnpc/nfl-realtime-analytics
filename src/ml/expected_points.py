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
            'score_differential', 'posteam_is_home', 'qtr',
            'goal_to_go', 'shotgun', 'no_huddle'
        ]
        
    def prepare_data(self, df):
        df = df.copy()
        
        # Convert posteam_type to binary
        if 'posteam_type' in df.columns:
            df['posteam_is_home'] = (df['posteam_type'] == 'home').astype(int)
        else:
            df['posteam_is_home'] = 0
        
        # Ensure numeric features
        for col in self.feature_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Fill missing with defaults
        df['goal_to_go'] = df['goal_to_go'].fillna(0).astype(int)
        df['shotgun'] = df['shotgun'].fillna(0).astype(int)
        df['no_huddle'] = df['no_huddle'].fillna(0).astype(int)
        df['half_seconds_remaining'] = df['half_seconds_remaining'].fillna(1800)
        df['posteam_timeouts_remaining'] = df['posteam_timeouts_remaining'].fillna(3)
        df['defteam_timeouts_remaining'] = df['defteam_timeouts_remaining'].fillna(3)
        df['score_differential'] = df['score_differential'].fillna(0)
        df['qtr'] = df['qtr'].fillna(1)
        
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
        print(f"Total rows: {len(df)}")
        
        df = self.prepare_data(df)
        
        # Target: ep (expected points)
        if 'ep' not in df.columns:
            print("Warning: 'ep' column not found. Cannot train.")
            return None
        
        # Filter to valid plays
        df = df[df['play_type'].isin(['run', 'pass'])].copy()
        df = df.dropna(subset=['ep', 'down', 'ydstogo', 'yardline_100'])
        print(f"After filtering: {len(df)} plays")
        
        X = df[self.feature_columns].fillna(0)
        y = df['ep']
        
        print(f"\nTarget (EP) stats:")
        print(f"  Mean: {y.mean():.4f}")
        print(f"  Std: {y.std():.4f}")
        print(f"  Min: {y.min():.4f}, Max: {y.max():.4f}")
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print(f"\nTraining set: {len(X_train)}")
        print(f"Test set: {len(X_test)}")
        
        self.model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            min_child_weight=10,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        print("\nTraining Expected Points Model...")
        self.model.fit(X_train, y_train)
        
        preds = self.model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)
        
        print(f"\n{'='*50}")
        print(f"RESULTS")
        print(f"{'='*50}")
        print(f"RMSE: {rmse:.4f}")
        print(f"R2: {r2:.4f}")
        
        print(f"\nTop Feature Importance:")
        importance = self.model.feature_importances_
        for feat, imp in sorted(zip(self.feature_columns, importance), key=lambda x: -x[1])[:5]:
            print(f"  {feat}: {imp:.4f}")
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'feature_columns': self.feature_columns
            }, save_path)
            print(f"\nSaved to {save_path}")
        
        return r2
            
    def predict(self, features):
        if self.model is None:
            raise ValueError("Model not trained")
        
        if isinstance(features, dict):
            # Handle posteam_type conversion
            if 'posteam_type' in features:
                features['posteam_is_home'] = 1 if features['posteam_type'] == 'home' else 0
            elif 'posteam_is_home' not in features:
                features['posteam_is_home'] = 0
                 
            df = pd.DataFrame([features])
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            
            X = df[self.feature_columns].fillna(0)
            return float(self.model.predict(X)[0])
            
        return self.model.predict(features)

    def load(self, path):
        data = joblib.load(path)
        self.model = data['model']
        self.feature_columns = data['feature_columns']


if __name__ == "__main__":
    data_paths = [
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2016.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2017.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2018.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2019.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2020.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2021.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2022.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2023.csv",
        "/Users/adithyahnair/nfl-project/data/raw/pbp_2024.csv"
    ]
    
    model = ExpectedPointsModel()
    model.train(data_paths, save_path="/Users/adithyahnair/nfl-project/models/expected_points.joblib")
