"""
Scoring Probability Model
Predicts probability of next score type: TD, FG, Safety, No Score (for both teams)
"""

import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

class ScoringProbabilityModel:
    def __init__(self):
        self.models = {}
        self.feature_columns = [
            'down', 'ydstogo', 'yardline_100', 'half_seconds_remaining',
            'posteam_timeouts_remaining', 'defteam_timeouts_remaining',
            'score_differential', 'posteam_is_home', 'qtr', 'goal_to_go'
        ]
        self.prob_columns = [
            'td_prob', 'fg_prob', 'safety_prob', 'no_score_prob',
            'opp_td_prob', 'opp_fg_prob', 'opp_safety_prob'
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
        
        df['goal_to_go'] = df['goal_to_go'].fillna(0).astype(int)
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
        
        # Filter to valid plays
        df = df[df['play_type'].isin(['run', 'pass'])].copy()
        
        # Check all prob columns exist
        missing = [col for col in self.prob_columns if col not in df.columns]
        if missing:
            print(f"Warning: Missing columns: {missing}")
            return None
        
        df = df.dropna(subset=self.prob_columns + ['down', 'ydstogo', 'yardline_100'])
        print(f"After filtering: {len(df)} plays")
        
        X = df[self.feature_columns].fillna(0)
        
        # Train a model for each probability
        results = {}
        
        for prob_col in self.prob_columns:
            print(f"\nTraining {prob_col} model...")
            y = df[prob_col]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            model = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=5,
                learning_rate=0.05,
                min_child_weight=10,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X_train, y_train)
            
            preds = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, preds))
            r2 = r2_score(y_test, preds)
            
            self.models[prob_col] = model
            results[prob_col] = {'rmse': rmse, 'r2': r2}
            print(f"  RMSE: {rmse:.4f}, R2: {r2:.4f}")
        
        print(f"\n{'='*50}")
        print("RESULTS SUMMARY")
        print(f"{'='*50}")
        for prob_col, metrics in results.items():
            print(f"  {prob_col}: R2={metrics['r2']:.4f}")
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            joblib.dump({
                'models': self.models,
                'feature_columns': self.feature_columns,
                'prob_columns': self.prob_columns
            }, save_path)
            print(f"\nSaved to {save_path}")
        
        return results

    def predict_proba(self, features):
        if not self.models:
            raise ValueError("Models not trained")
            
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
            
            probs = {}
            for prob_col, model in self.models.items():
                probs[prob_col] = float(model.predict(X)[0])
            
            # Normalize to sum to 1
            total = sum(probs.values())
            if total > 0:
                probs = {k: v/total for k, v in probs.items()}
            
            return probs
            
        # Batch prediction
        results = {}
        for prob_col, model in self.models.items():
            results[prob_col] = model.predict(features)
        return results

    def load(self, path):
        data = joblib.load(path)
        self.models = data['models']
        self.feature_columns = data['feature_columns']
        self.prob_columns = data['prob_columns']


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
    
    model = ScoringProbabilityModel()
    model.train(data_paths, save_path="/Users/adithyahnair/nfl-project/models/scoring_probability.joblib")
