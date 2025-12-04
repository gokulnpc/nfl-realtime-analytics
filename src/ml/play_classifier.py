"""
Play Type Classifier - Final Version
5-class hierarchical: inside_run, outside_run, screen, short_pass, deep_pass
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import xgboost as xgb
import joblib
import os
import re

class PlayClassifier:
    def __init__(self):
        self.model_run_pass = None
        self.model_run_type = None
        self.model_pass_type = None
        self.le_pass = LabelEncoder()
        self.feature_columns = [
            'down', 'ydstogo', 'yardline_100', 'score_differential',
            'qtr', 'half_seconds_remaining', 'wp',
            'posteam_timeouts_remaining', 'defteam_timeouts_remaining',
            'shotgun', 'no_huddle', 'defenders_in_box', 'number_of_pass_rushers',
            'n_rb', 'n_te', 'n_wr',
            'goal_to_go', 'short_yardage', 'long_yardage', 'red_zone',
            'late_down', 'two_minute_drill',
            'heavy_box', 'light_box', 'extra_rushers',
            'pass_heavy_situation', 'run_heavy_situation',
            'heavy_personnel', 'spread_personnel'
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
        df = df[df['play_type'].isin(['run', 'pass'])].copy()
        df = df[df['qb_scramble'] != 1].copy()
        
        df['is_pass'] = (df['play_type'] == 'pass').astype(int)
        
        def get_run_type(row):
            if row['play_type'] != 'run':
                return None
            run_gap = row.get('run_gap', '')
            run_loc = row.get('run_location', '')
            if run_loc == 'middle' or run_gap == 'guard':
                return 'inside_run'
            return 'outside_run'
        
        def get_pass_type(row):
            if row['play_type'] != 'pass':
                return None
            if row.get('route') == 'SCREEN':
                return 'screen'
            if row.get('pass_length') == 'deep':
                return 'deep_pass'
            return 'short_pass'
        
        def get_5class(row):
            rt = get_run_type(row)
            if rt:
                return rt
            return get_pass_type(row)
        
        df['run_type'] = df.apply(get_run_type, axis=1)
        df['pass_type'] = df.apply(get_pass_type, axis=1)
        df['class_5'] = df.apply(get_5class, axis=1)
        
        df['score_differential'] = df['posteam_score'] - df['defteam_score']
        
        personnel_data = df['offense_personnel'].apply(self.parse_personnel)
        df['n_rb'] = personnel_data.apply(lambda x: x[0])
        df['n_te'] = personnel_data.apply(lambda x: x[1])
        df['n_wr'] = personnel_data.apply(lambda x: x[2])
        
        df['goal_to_go'] = df['goal_to_go'].fillna(0).astype(int)
        df['short_yardage'] = (df['ydstogo'] <= 3).astype(int)
        df['long_yardage'] = (df['ydstogo'] >= 8).astype(int)
        df['red_zone'] = (df['yardline_100'] <= 20).astype(int)
        df['late_down'] = (df['down'] >= 3).astype(int)
        df['two_minute_drill'] = ((df['half_seconds_remaining'] <= 120) & (df['score_differential'].abs() <= 8)).astype(int)
        df['heavy_box'] = (df['defenders_in_box'] >= 7).astype(int)
        df['light_box'] = (df['defenders_in_box'] <= 5).astype(int)
        df['extra_rushers'] = (df['number_of_pass_rushers'] >= 5).astype(int)
        df['pass_heavy_situation'] = (((df['down'] >= 3) & (df['ydstogo'] >= 5)) | ((df['score_differential'] < -8) & (df['qtr'] >= 3))).astype(int)
        df['run_heavy_situation'] = (((df['down'] <= 2) & (df['ydstogo'] <= 4)) | ((df['score_differential'] > 14) & (df['qtr'] >= 3))).astype(int)
        df['heavy_personnel'] = ((df['n_rb'] >= 2) | (df['n_te'] >= 2)).astype(int)
        df['spread_personnel'] = ((df['n_wr'] >= 3) & (df['shotgun'] == 1)).astype(int)
        
        for col in self.feature_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        df = df.dropna(subset=['down', 'ydstogo', 'class_5'])
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
        print(f"After filtering: {len(df)} plays")
        
        X = df[self.feature_columns].fillna(0)
        
        # Stage 1: Run vs Pass
        print("\n[STAGE 1] Run vs Pass")
        y1 = df['is_pass']
        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            X, y1, df.index, test_size=0.2, random_state=42, stratify=y1
        )
        
        self.model_run_pass = xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42, n_jobs=-1
        )
        self.model_run_pass.fit(X_train, y_train)
        acc1 = accuracy_score(y_test, self.model_run_pass.predict(X_test))
        print(f"  Accuracy: {acc1*100:.1f}%")
        
        # Stage 2a: Inside vs Outside Run
        print("\n[STAGE 2a] Inside vs Outside Run")
        df_runs = df[df['run_type'].notna()]
        X_runs = df_runs[self.feature_columns].fillna(0)
        y_runs = (df_runs['run_type'] == 'outside_run').astype(int)
        X_tr, X_te, y_tr, y_te = train_test_split(X_runs, y_runs, test_size=0.2, random_state=42, stratify=y_runs)
        
        self.model_run_type = xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42, n_jobs=-1
        )
        self.model_run_type.fit(X_tr, y_tr)
        acc2a = accuracy_score(y_te, self.model_run_type.predict(X_te))
        print(f"  Accuracy: {acc2a*100:.1f}%")
        
        # Stage 2b: Pass Type (screen, short, deep)
        print("\n[STAGE 2b] Screen vs Short vs Deep Pass")
        df_passes = df[df['pass_type'].notna()]
        X_passes = df_passes[self.feature_columns].fillna(0)
        y_passes = self.le_pass.fit_transform(df_passes['pass_type'])
        X_tr, X_te, y_tr, y_te = train_test_split(X_passes, y_passes, test_size=0.2, random_state=42, stratify=y_passes)
        
        self.model_pass_type = xgb.XGBClassifier(
            n_estimators=400, max_depth=7, learning_rate=0.03, random_state=42, n_jobs=-1
        )
        self.model_pass_type.fit(X_tr, y_tr)
        acc2b = accuracy_score(y_te, self.model_pass_type.predict(X_te))
        print(f"  Accuracy: {acc2b*100:.1f}%")
        
        # Combined evaluation
        print("\n[COMBINED 5-CLASS]")
        df_test = df.loc[idx_test]
        X_test_all = df_test[self.feature_columns].fillna(0)
        
        y_pred = []
        for _, row in X_test_all.iterrows():
            is_pass = self.model_run_pass.predict([row.values])[0]
            if is_pass:
                p = self.model_pass_type.predict([row.values])[0]
                y_pred.append(self.le_pass.classes_[p])
            else:
                is_out = self.model_run_type.predict([row.values])[0]
                y_pred.append('outside_run' if is_out else 'inside_run')
        
        acc = accuracy_score(df_test['class_5'].values, y_pred)
        print(f"  Accuracy: {acc*100:.1f}%")
        print(classification_report(df_test['class_5'].values, y_pred, zero_division=0))
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            joblib.dump({
                'model_run_pass': self.model_run_pass,
                'model_run_type': self.model_run_type,
                'model_pass_type': self.model_pass_type,
                'le_pass': self.le_pass,
                'feature_columns': self.feature_columns
            }, save_path)
            print(f"\nSaved to {save_path}")
        
        return acc
    
    def predict(self, features):
        if isinstance(features, dict):
            features = pd.DataFrame([features])[self.feature_columns].fillna(0).values[0]
        is_pass = self.model_run_pass.predict([features])[0]
        if is_pass:
            p = self.model_pass_type.predict([features])[0]
            return self.le_pass.classes_[p]
        else:
            return 'outside_run' if self.model_run_type.predict([features])[0] else 'inside_run'
    
    def load(self, model_path):
        data = joblib.load(model_path)
        self.model_run_pass = data['model_run_pass']
        self.model_run_type = data['model_run_type']
        self.model_pass_type = data['model_pass_type']
        self.le_pass = data['le_pass']
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
    
    classifier = PlayClassifier()
    classifier.train(data_paths, save_path="/Users/adithyahnair/nfl-project/models/play_classifier.joblib")
