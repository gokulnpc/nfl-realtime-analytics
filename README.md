# NFL Real-Time Play Breakdown & Pressure-Rate Prediction

## Setup

### 1. Clone the repo
```
git clone https://github.com/gokulnpc/nfl-realtime-analytics.git
cd nfl-realtime-analytics
```

### 2. Install dependencies
```
pip install pyspark pandas boto3 nfl_data_py
brew install openjdk@17
```

### 3. Download the data
```
mkdir -p data/raw
cd data/raw
kaggle datasets download -d maxhorowitz/nflplaybyplay2009to2016
unzip nflplaybyplay2009to2016.zip
```

Then in Python:
```python
import nfl_data_py as nfl
nfl.import_pbp_data([2023]).to_csv('pbp_2023.csv', index=False)
nfl.import_pbp_data([2024]).to_csv('pbp_2024.csv', index=False)
```

### 4. Configure AWS CLI
```
aws configure
```
Enter the shared Access Key, Secret Key, region: us-east-1, output: json

### 5. Recreate Kinesis streams (if needed)
```
aws kinesis create-stream --stream-name nfl-play-events --shard-count 1
aws kinesis create-stream --stream-name nfl-tracking-frames --shard-count 1
```

### 6. Test the streaming pipeline locally
```
python3 src/streaming/create_test_data.py
python3 src/streaming/spark_streaming_job.py console file
```

## Project Structure
```
nfl-project/
├── data/
│   ├── raw/                 # Historical NFL data (download separately)
│   └── streaming-input/     # Test data for local streaming
├── docs/
│   └── schemas.md           # Data schemas
└── src/
    ├── simulator/
    │   └── replay_data.py   # Replay historical data
    └── streaming/
        ├── create_test_data.py      # Generate test files
        ├── kinesis_producer.py      # Send data to Kinesis
        └── spark_streaming_job.py   # Main streaming job
```

## AWS Resources
- Kinesis: `nfl-play-events`, `nfl-tracking-frames`
- S3: `s3://nfl-analytics-an4465/`

## Remaining Tasks
1. Build ESPN live data poller (Ingestion)
2. Train ML models for play classification & pressure prediction
3. Build real-time dashboard (Streamlit/React)
4. Write final report

## Team
- Aditya Maheshwari
- Adithyah Nair
- Amogh Krishna
- Gokuleshwaran Narayanan
- Sumisha Mohan
```
