"""
Pressure Predictor - Final Version
Predicts probability of QB pressure on pass plays
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score
import xgboost as xgb
import joblib
import os
import re

class PressurePredictor:
    def __init__(self):
        self.model = None
        self.feature_columns = [
            'down', 'ydstogo', 'yardline_100', 'score_differential',
            'qtr', 'half_seconds_remaining', 'wp',
            'posteam_timeouts_remaining', 'defteam_timeouts_remaining',
            'shotgun', 'no_huddle', 'defenders_in_box', 'number_of_pass_rushers',
            'n_rb', 'n_te', 'n_wr',
            'blitz', 'obvious_passing', 'red_zone', 'late_game', 'rushers_ratio'
        ]
    
    def parse_personnel(self, personnel_str):
        if pd.isna(personnel_str):
            return 1, 1, 3
        rb = re.search(r'(\d+)\s*RB', personnel_str)
        te = re.search(r'(\d+)\s*TE', personnel_str)
        wr = re.search(r'(\d+)\s*WR', personnel_str)
        fb = re.search(r'(\d+)\s*FB', personnel_str)
        n_rb = int(rb.group(1)) if rb else 0
        n_rb += int(fb.group(1)) if fb else 0
        n_te = int(te.group(1)) if te else 0
        n_wr = int(wr.group(1)) if wr else 0
        return n_rb, n_te, n_wr
    
    def prepare_data(self, df):
        # Filter to pass plays only
        df = df[df['play_type'] == 'pass'].copy()
        df = df[df['qb_scramble'] != 1].copy()
        
        # Target: was_pressure
        df = df[df['was_pressure'].notna()].copy()
        df['pressure'] = df['was_pressure'].astype(int)
        
        df['score_differential'] = df['posteam_score'] - df['defteam_score']
        
        personnel_data = df['offense_personnel'].apply(self.parse_personnel)
        df['n_rb'] = personnel_data.apply(lambda x: x[0])
        df['n_te'] = personnel_data.apply(lambda x: x[1])
        df['n_wr'] = personnel_data.apply(lambda x: x[2])
        
        # Engineered features
        df['blitz'] = (df['number_of_pass_rushers'] >= 5).astype(int)
        df['obvious_passing'] = ((df['down'] >= 3) & (df['ydstogo'] >= 7)).astype(int)
        df['red_zone'] = (df['yardline_100'] <= 20).astype(int)
        df['late_game'] = ((df['qtr'] >= 4) & (df['half_seconds_remaining'] <= 300)).astype(int)
        df['rushers_ratio'] = df['number_of_pass_rushers'] / (df['defenders_in_box'] + 1)
        
        for col in self.feature_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        df = df.dropna(subset=['down', 'ydstogo', 'pressure'])
        return df.reset_index(drop=True)
    
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
        print(f"After filtering: {len(df)} pass plays")
        
        print(f"\nPressure distribution:")
        print(f"  No pressure: {(df['pressure'] == 0).sum()}")
        print(f"  Pressure: {(df['pressure'] == 1).sum()}")
        print(f"  Pressure rate: {df['pressure'].mean()*100:.1f}%")
        
        X = df[self.feature_columns].fillna(0)
        y = df['pressure']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"\nTraining set: {len(X_train)}")
        print(f"Test set: {len(X_test)}")
        
        # Handle class imbalance
        scale_pos = (y_train == 0).sum() / (y_train == 1).sum()
        
        print("\nTraining XGBoost model...")
        self.model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=4,
            learning_rate=0.01,
            min_child_weight=5,
            subsample=0.7,
            colsample_bytree=0.7,
            gamma=0.2,
            reg_alpha=0.5,
            reg_lambda=2,
            scale_pos_weight=scale_pos,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        print(f"\n{'='*50}")
        print(f"RESULTS")
        print(f"{'='*50}")
        print(f"Accuracy: {acc*100:.1f}%")
        print(f"AUC-ROC: {auc*100:.1f}%")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['No Pressure', 'Pressure']))
        
        print(f"\nTop 10 Feature Importance:")
        importance = self.model.feature_importances_
        for feat, imp in sorted(zip(self.feature_columns, importance), key=lambda x: -x[1])[:10]:
            print(f"  {feat}: {imp:.4f}")
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            joblib.dump({
                'model': self.model,
                'feature_columns': self.feature_columns
            }, save_path)
            print(f"\nSaved to {save_path}")
        
        return auc
    
    def predict(self, features):
        if self.model is None:
            raise ValueError("Model not trained")
        if isinstance(features, dict):
            features = pd.DataFrame([features])[self.feature_columns].fillna(0)
        return self.model.predict_proba(features)[:, 1]
    
    def load(self, model_path):
        data = joblib.load(model_path)
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
    
    predictor = PressurePredictor()
    predictor.train(data_paths, save_path="/Users/adithyahnair/nfl-project/models/pressure_predictor.joblib")
