"""
PySpark Feature Engineering Pipeline
Processes raw NFL data at scale for model training
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import os
import glob

def create_spark_session():
    return SparkSession.builder \
        .appName("NFL-Feature-Engineering") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "8") \
        .master("local[*]") \
        .getOrCreate()

def safe_int(col_name):
    """Safely cast to int via double to handle '1.0' format"""
    return col(col_name).cast("double").cast("int")

def main():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    print("="*60)
    print("🏈 NFL Big Data Feature Engineering Pipeline")
    print("="*60)
    
    data_path = "/Users/adithyahnair/nfl-project/data/raw/"
    
    print("\n📂 Loading play-by-play data with PySpark...")
    
    csv_files = glob.glob(f"{data_path}pbp_*.csv")
    print(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"  - {os.path.basename(f)}")
    
    file_paths = [f"file://{f}" for f in csv_files]
    
    df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .csv(file_paths)
    
    total_rows = df.count()
    print(f"\n✅ Loaded {total_rows:,} total plays")
    print(f"✅ Columns: {len(df.columns)}")
    
    plays_df = df.filter(col("play_type").isin(["run", "pass"]))
    filtered_count = plays_df.count()
    print(f"✅ Filtered to {filtered_count:,} run/pass plays")
    
    print("\n🔧 Engineering features...")
    
    features_df = plays_df.select(
        col("game_id"),
        col("play_id"),
        safe_int("season").alias("season"),
        safe_int("week").alias("week"),
        col("posteam"),
        col("defteam"),
        safe_int("down").alias("down"),
        safe_int("ydstogo").alias("ydstogo"),
        safe_int("yardline_100").alias("yardline_100"),
        safe_int("qtr").alias("qtr"),
        col("half_seconds_remaining").cast("double").cast("int").alias("half_seconds_remaining"),
        col("score_differential").cast("double").cast("int").alias("score_differential"),
        col("shotgun").cast("double").cast("int").alias("shotgun"),
        col("no_huddle").cast("double").cast("int").alias("no_huddle"),
        col("defenders_in_box").cast("double").cast("int").alias("defenders_in_box"),
        col("number_of_pass_rushers").cast("double").cast("int").alias("number_of_pass_rushers"),
        col("ep").cast("double").alias("ep"),
        col("wp").cast("double").alias("wp"),
        col("epa").cast("double").alias("epa"),
        col("play_type"),
        col("posteam_type"),
        when(col("yardline_100").cast("double") <= 20, 1).otherwise(0).alias("red_zone"),
        when(col("yardline_100").cast("double") <= 10, 1).otherwise(0).alias("goal_to_go_territory"),
        when(col("ydstogo").cast("double") <= 3, 1).otherwise(0).alias("short_yardage"),
        when(col("ydstogo").cast("double") >= 8, 1).otherwise(0).alias("long_yardage"),
        when(col("down").cast("double") >= 3, 1).otherwise(0).alias("late_down"),
        when((col("qtr").cast("double") == 4) & (col("half_seconds_remaining").cast("double") <= 300), 1).otherwise(0).alias("late_game"),
        when(col("defenders_in_box").cast("double") >= 7, 1).otherwise(0).alias("heavy_box"),
        when(col("defenders_in_box").cast("double") <= 5, 1).otherwise(0).alias("light_box"),
        when(col("number_of_pass_rushers").cast("double") >= 5, 1).otherwise(0).alias("blitz"),
        when(col("posteam_type") == "home", 1).otherwise(0).alias("posteam_is_home"),
        when(col("play_type") == "pass", 1).otherwise(0).alias("is_pass")
    ).na.drop(subset=["down", "ydstogo", "yardline_100"])
    
    final_count = features_df.count()
    print(f"✅ Final dataset: {final_count:,} plays with {len(features_df.columns)} features")
    
    print("\n📊 Sample data:")
    features_df.select(
        "season", "posteam", "defteam", "down", "ydstogo", 
        "yardline_100", "ep", "play_type", "red_zone", "blitz"
    ).show(10)
    
    print("\n📈 Season-by-Season Statistics:")
    season_stats = features_df.groupBy("season").agg(
        count("*").alias("plays"),
        round(avg("ep"), 2).alias("avg_ep"),
        round(avg("epa"), 3).alias("avg_epa"),
        round(avg("is_pass") * 100, 1).alias("pass_rate_pct")
    ).orderBy("season")
    season_stats.show(10)
    
    print("\n📈 Team Rankings by EPA:")
    team_stats = features_df.groupBy("posteam").agg(
        count("*").alias("plays"),
        round(avg("epa"), 3).alias("avg_epa"),
        round(avg("is_pass") * 100, 1).alias("pass_rate")
    ).orderBy(desc("avg_epa"))
    team_stats.show(10)
    
    output_path = "/Users/adithyahnair/nfl-project/data/processed"
    os.makedirs(output_path, exist_ok=True)
    
    print(f"\n💾 Saving to Parquet format...")
    features_df.write \
        .mode("overwrite") \
        .partitionBy("season") \
        .parquet(f"file://{output_path}/plays_features")
    
    print(f"✅ Saved to {output_path}/plays_features/")
    
    print("\n" + "="*60)
    print("✅ PySpark Feature Engineering Complete!")
    print("="*60)
    
    spark.stop()

if __name__ == "__main__":
    main()
