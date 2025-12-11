"""
PySpark Stream Processor
Reads from Kinesis → Processes → Writes to Parquet
FastAPI reads from Parquet for predictions
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, when, lit, udf
from pyspark.sql.types import *
import os
import json
import boto3
import time

# Play schema
PLAY_SCHEMA = StructType([
    StructField("game_id", StringType(), True),
    StructField("down", IntegerType(), True),
    StructField("ydstogo", IntegerType(), True),
    StructField("yardline_100", IntegerType(), True),
    StructField("qtr", IntegerType(), True),
    StructField("half_seconds_remaining", IntegerType(), True),
    StructField("score_differential", IntegerType(), True),
    StructField("posteam", StringType(), True),
    StructField("defteam", StringType(), True),
    StructField("home_team", StringType(), True),
    StructField("away_team", StringType(), True),
    StructField("home_score", IntegerType(), True),
    StructField("away_score", IntegerType(), True),
    StructField("goal_to_go", IntegerType(), True),
    StructField("shotgun", IntegerType(), True),
    StructField("no_huddle", IntegerType(), True),
    StructField("defenders_in_box", IntegerType(), True),
    StructField("number_of_pass_rushers", IntegerType(), True),
    StructField("timestamp", StringType(), True),
    StructField("source", StringType(), True),
    StructField("description", StringType(), True),
    StructField("posteam_type", StringType(), True)
])

OUTPUT_PATH = "/Users/adithyahnair/nfl-project/data/live_predictions"

def create_spark_session():
    return SparkSession.builder \
        .appName("NFL-Stream-Processor") \
        .config("spark.driver.memory", "2g") \
        .config("spark.sql.shuffle.partitions", "2") \
        .master("local[2]") \
        .getOrCreate()

# UDF for Expected Points - use Python's round, not PySpark's
def calc_ep(down, ydstogo, yardline_100, qtr, seconds_remaining, score_diff):
    if down is None or yardline_100 is None:
        return 0.0
    
    # Base EP from field position
    ep = (100 - yardline_100) * 0.06 - 1.0
    
    # Down adjustment
    if down == 1:
        ep += 0.5
    elif down == 2:
        ep += 0.1
    elif down == 3:
        ep -= 0.4
    elif down == 4:
        ep -= 1.2
    
    # Distance adjustment
    if ydstogo is not None:
        if ydstogo <= 3:
            ep += 0.4
        elif ydstogo >= 10:
            ep -= 0.3
    
    # Red zone boost
    if yardline_100 <= 20:
        ep += 1.2
    if yardline_100 <= 10:
        ep += 0.8
    if yardline_100 <= 5:
        ep += 0.5
    
    # Use Python's built-in round
    return float(int(ep * 100) / 100)

calc_expected_points = udf(calc_ep, DoubleType())

# UDF for TD Probability
def calc_td(yardline_100, down, ydstogo):
    if yardline_100 is None:
        return 0.0
    
    if yardline_100 <= 5:
        prob = 0.60
    elif yardline_100 <= 10:
        prob = 0.45
    elif yardline_100 <= 20:
        prob = 0.30
    elif yardline_100 <= 50:
        prob = 0.18
    else:
        prob = 0.10
    
    # Down adjustment
    if down == 1:
        prob *= 1.1
    elif down == 4:
        prob *= 0.6
    
    return min(float(int(prob * 1000) / 1000), 0.95)

calc_td_prob = udf(calc_td, DoubleType())

# UDF for FG Probability
def calc_fg(yardline_100):
    if yardline_100 is None:
        return 0.0
    
    fg_distance = yardline_100 + 17
    
    if fg_distance <= 30:
        return 0.90
    elif fg_distance <= 40:
        return 0.80
    elif fg_distance <= 50:
        return 0.65
    elif fg_distance <= 55:
        return 0.45
    else:
        return 0.25

calc_fg_prob = udf(calc_fg, DoubleType())

# UDF for Pressure Risk
def calc_pressure(pass_rushers):
    if pass_rushers is None:
        return "medium"
    
    if pass_rushers >= 5:
        return "high"
    elif pass_rushers <= 3:
        return "low"
    else:
        return "medium"

calc_pressure_risk = udf(calc_pressure, StringType())

# UDF for Pass Probability
def calc_pass_prob(down, ydstogo):
    if ydstogo is None:
        return 0.55
    
    if ydstogo >= 7:
        return 0.75
    elif down is not None and down >= 3:
        return 0.70
    else:
        return 0.55

calc_pass_probability = udf(calc_pass_prob, DoubleType())

def fetch_from_kinesis():
    """Fetch records from Kinesis using boto3"""
    from dotenv import load_dotenv
    load_dotenv("/Users/adithyahnair/nfl-project/.env")
    
    kinesis = boto3.client('kinesis', region_name='us-east-1')
    
    try:
        response = kinesis.describe_stream(StreamName='nfl-play-stream')
        shard_id = response['StreamDescription']['Shards'][0]['ShardId']
        
        shard_iterator = kinesis.get_shard_iterator(
            StreamName='nfl-play-stream',
            ShardId=shard_id,
            ShardIteratorType='LATEST'
        )['ShardIterator']
        
        return kinesis, shard_iterator
    except Exception as e:
        print(f"Error connecting to Kinesis: {e}")
        return None, None

def process_and_save(spark, records):
    """Process records with PySpark and save to Parquet"""
    
    if not records:
        return
    
    # Create DataFrame from records
    df = spark.createDataFrame(records, schema=PLAY_SCHEMA)
    
    # Add predictions using PySpark UDFs
    predictions_df = df \
        .withColumn("expected_points", 
            calc_expected_points(
                col("down"), col("ydstogo"), col("yardline_100"),
                col("qtr"), col("half_seconds_remaining"), col("score_differential")
            )) \
        .withColumn("td_prob", 
            calc_td_prob(col("yardline_100"), col("down"), col("ydstogo"))) \
        .withColumn("fg_prob", 
            calc_fg_prob(col("yardline_100"))) \
        .withColumn("no_score_prob", 
            lit(1.0) - col("td_prob") - col("fg_prob") * lit(0.5)) \
        .withColumn("pressure_risk",
            calc_pressure_risk(col("number_of_pass_rushers"))) \
        .withColumn("pass_probability",
            calc_pass_probability(col("down"), col("ydstogo"))) \
        .withColumn("run_probability",
            lit(1.0) - col("pass_probability")) \
        .withColumn("predicted_play",
            when(col("ydstogo") <= 2, lit("run"))
            .when(col("down") == 4, lit("punt_or_fg"))
            .otherwise(lit("pass"))) \
        .withColumn("processed_at", current_timestamp())
    
    # Show in console
    print(f"\n{'='*70}")
    print(f"🏈 PYSPARK PROCESSED {predictions_df.count()} PLAYS")
    print(f"{'='*70}")
    
    predictions_df.select(
        "posteam", "defteam", "down", "ydstogo", "yardline_100", "qtr",
        "expected_points", "td_prob", "fg_prob", "pressure_risk"
    ).show(truncate=False)
    
    # Save to Parquet
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    predictions_df.write \
        .mode("overwrite") \
        .parquet(f"file://{OUTPUT_PATH}/latest")
    
    print(f"✅ Saved to {OUTPUT_PATH}/latest")

def run_streaming():
    """Main streaming loop"""
    
    print("\n" + "="*70)
    print("🏈 NFL PYSPARK STREAM PROCESSOR")
    print("="*70)
    print(f"Output Path: {OUTPUT_PATH}")
    print("="*70 + "\n")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    kinesis, shard_iterator = fetch_from_kinesis()
    
    if not kinesis:
        print("❌ Could not connect to Kinesis")
        spark.stop()
        return
    
    print("✅ Connected to Kinesis stream: nfl-play-stream")
    print("🔄 Polling every 3 seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            response = kinesis.get_records(ShardIterator=shard_iterator, Limit=100)
            shard_iterator = response['NextShardIterator']
            
            records = []
            for record in response['Records']:
                try:
                    data = json.loads(record['Data'].decode('utf-8'))
                    records.append(data)
                except:
                    continue
            
            if records:
                process_and_save(spark, records)
            else:
                print(".", end="", flush=True)
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping stream processor...")
    finally:
        spark.stop()
        print("✅ Spark session stopped")

if __name__ == "__main__":
    run_streaming()
