"""
PySpark Structured Streaming Job
Reads from Kinesis or local files, processes play data, writes to S3 or console
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_json, struct, lit, when,
    current_timestamp, window, avg, count, max as spark_max
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, TimestampType
)

# Schema for play events
PLAY_EVENT_SCHEMA = StructType([
    StructField("game_id", StringType(), True),
    StructField("play_id", IntegerType(), True),
    StructField("quarter", IntegerType(), True),
    StructField("down", IntegerType(), True),
    StructField("ydstogo", IntegerType(), True),
    StructField("yardline_100", IntegerType(), True),
    StructField("posteam", StringType(), True),
    StructField("defteam", StringType(), True),
    StructField("play_type", StringType(), True),
    StructField("shotgun", IntegerType(), True),
    StructField("no_huddle", IntegerType(), True),
    StructField("offense_formation", StringType(), True),
    StructField("defenders_in_box", IntegerType(), True),
    StructField("number_of_pass_rushers", IntegerType(), True),
    StructField("was_pressure", IntegerType(), True),
    StructField("time_to_throw", DoubleType(), True),
    StructField("epa", DoubleType(), True),
    StructField("event_time", StringType(), True)
])


def create_spark_session():
    """Initialize Spark session."""
    return (SparkSession.builder
            .appName("NFL-RealTime-Analytics")
            .config("spark.sql.streaming.checkpointLocation", "/tmp/nfl-checkpoints")
            .getOrCreate())


def calculate_pressure_probability(df):
    """
    Calculate pressure probability based on play features.
    """
    return df.withColumn(
        "pressure_probability",
        when(col("number_of_pass_rushers") >= 5, 0.7)
        .when(col("number_of_pass_rushers") >= 4, 0.5)
        .when(col("defenders_in_box") >= 7, 0.6)
        .when(col("defenders_in_box") >= 6, 0.4)
        .otherwise(0.25)
    )


def calculate_chaos_score(df):
    """
    Calculate chaos score (0-100) based on play situation.
    """
    return df.withColumn(
        "chaos_score",
        (
            when(col("down") >= 3, 30).otherwise(col("down") * 5) +
            when(col("ydstogo") >= 10, 25)
            .when(col("ydstogo") >= 5, 15)
            .otherwise(5) +
            when(col("yardline_100") <= 20, 25)
            .when(col("yardline_100") <= 40, 15)
            .otherwise(5) +
            when(col("number_of_pass_rushers") >= 5, 20)
            .when(col("number_of_pass_rushers") >= 4, 10)
            .otherwise(5)
        )
    )


def predict_play_type(df):
    """
    Simple rule-based play type prediction.
    """
    return df.withColumn(
        "predicted_play_type",
        when((col("down") == 1) & (col("ydstogo") == 10), "run")
        .when((col("down") >= 3) & (col("ydstogo") >= 7), "deep_pass")
        .when((col("down") >= 3) & (col("ydstogo") <= 3), "short_pass")
        .when(col("shotgun") == 1, "pass")
        .otherwise("run")
    )


def enrich_play_data(df):
    """Apply all enrichment transformations."""
    enriched = df
    enriched = calculate_pressure_probability(enriched)
    enriched = calculate_chaos_score(enriched)
    enriched = predict_play_type(enriched)
    enriched = enriched.withColumn("processed_at", current_timestamp())
    return enriched


def read_from_files(spark, input_path):
    """Read streaming data from files (for local testing)."""
    return (spark.readStream
            .schema(PLAY_EVENT_SCHEMA)
            .option("maxFilesPerTrigger", 1)
            .json(input_path))


def write_to_console(df):
    """Write streaming data to console (for testing)."""
    return (df.writeStream
            .format("console")
            .option("truncate", False)
            .outputMode("append")
            .start())


def write_to_parquet(df, output_path, checkpoint_path):
    """Write streaming data to parquet files."""
    return (df.writeStream
            .format("parquet")
            .option("path", output_path)
            .option("checkpointLocation", checkpoint_path)
            .partitionBy("game_id")
            .outputMode("append")
            .start())


def run_streaming_job(mode="console", input_source="file"):
    """
    Main entry point for streaming job.
    
    Args:
        mode: "console" for testing, "parquet" for file output
        input_source: "file" for local testing
    """
    print("Starting NFL Real-Time Analytics Streaming Job...")
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # Read from local files
    print("Reading from local files...")
    plays_df = read_from_files(spark, "file:///Users/adithyahnair/nfl-project/data/streaming-input")
    
    # Enrich the data
    enriched_df = enrich_play_data(plays_df)
    
    # Select output columns
    output_df = enriched_df.select(
        "game_id", "play_id", "quarter", "down", "ydstogo",
        "posteam", "defteam", "play_type", "predicted_play_type",
        "pressure_probability", "was_pressure", "time_to_throw",
        "chaos_score", "epa", "processed_at"
    )
    
    # Write to destination
    if mode == "parquet":
        print("Writing to parquet files...")
        query = write_to_parquet(
            output_df,
            "/tmp/nfl-streaming-output",
            "/tmp/nfl-checkpoints"
        )
    else:
        print("Writing to console...")
        query = write_to_console(output_df)
    
    query.awaitTermination()


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "console"
    run_streaming_job(mode=mode)
