"""
Spark MovieLens Recommendation Processing
Supports both local and EMR execution modes
Uses ID mapping to solve foreign key constraint issues
"""
import os
import sys
import traceback
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, lit, desc, current_timestamp

print("=" * 70)
print("Spark MovieLens Recommendation Processing")
print("=" * 70)

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
# Check if running in EMR mode with command line arguments
if len(sys.argv) >= 6:
    # EMR mode: spark-submit spark_recommendation.py <s3_input> <rds_host> <rds_db> <rds_user> <rds_password>
    EXECUTION_MODE = "emr"
    DATA_SOURCE = sys.argv[1]  # s3://bucket/input/
    RDS_HOST = sys.argv[2]
    RDS_DB = sys.argv[3]
    RDS_USER = sys.argv[4]
    RDS_PASSWORD = sys.argv[5]
    LIMIT_MOVIES = None  # Process all movies in EMR mode
    print(f"\nExecution Mode: EMR")
    print(f"Data Source: {DATA_SOURCE}")
else:
    # Local mode with default configuration
    EXECUTION_MODE = "local"
    DATA_SOURCE = "data"
    RDS_HOST = "recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com"
    RDS_DB = "recommendation_db"
    RDS_USER = "admin"
    RDS_PASSWORD = "RecommendDB2026!"
    LIMIT_MOVIES = 100  # Limit to 100 movies to prevent resource exhaustion
    print(f"\nExecution Mode: Local")
    print(f"Data Source: {DATA_SOURCE}/")

JDBC_URL = f"jdbc:mysql://{RDS_HOST}:3306/{RDS_DB}?useSSL=false&allowPublicKeyRetrieval=true"
print(f"Database: {RDS_HOST}/{RDS_DB}")

# ---------------------------------------------------------
# Create Spark Session
# ---------------------------------------------------------
print("\nCreating Spark Session...")

builder = SparkSession.builder.appName("MovieLens-Recommendation")

if EXECUTION_MODE == "local":
    # Local mode configuration
    builder = builder \
        .master("local[1]") \
        .config("spark.driver.memory", "512m") \
        .config("spark.executor.memory", "512m") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33")
else:
    # EMR mode configuration with S3 support
    builder = builder \
        .config("spark.jars.packages",
                "mysql:mysql-connector-java:8.0.33,"
                "org.apache.hadoop:hadoop-aws:3.3.2,"
                "com.amazonaws:aws-java-sdk-bundle:1.11.1026") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")

spark = builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("Spark Session created successfully")

try:
    # ---------------------------------------------------------
    # Read and Process Data
    # ---------------------------------------------------------
    print("\nReading and processing data...")

    # Read movies
    movies_path = f"{DATA_SOURCE}/movies.csv"
    movies_full = spark.read.csv(movies_path, header=True, inferSchema=True)

    if LIMIT_MOVIES:
        movies_df = movies_full.limit(LIMIT_MOVIES)
        print(f"Limited to {LIMIT_MOVIES} movies for local testing")
    else:
        movies_df = movies_full

    movie_count = movies_df.count()
    print(f"Loaded {movie_count} movies")

    # Get movie IDs for filtering ratings
    movie_ids = [row.movieId for row in movies_df.select("movieId").collect()]

    # Read ratings (only for selected movies)
    ratings_path = f"{DATA_SOURCE}/ratings.csv"
    ratings_full = spark.read.csv(ratings_path, header=True, inferSchema=True)
    ratings_df = ratings_full.filter(col("movieId").isin(movie_ids))

    rating_count = ratings_df.count()
    print(f"Loaded {rating_count} ratings")

    # Calculate rating statistics
    print("\nCalculating recommendations...")
    movie_stats = ratings_df.groupBy("movieId").agg(
        avg("rating").alias("avg_rating"),
        count("rating").alias("rating_count")
    )

    # Bayesian weighted average
    avg_rating_all = ratings_df.agg(avg("rating")).first()[0] or 3.0
    m = 10  # Minimum rating threshold
    C = avg_rating_all  # Global average rating

    print(f"Global average rating: {C:.2f}")

    recommendations = movie_stats.withColumn(
        "recommendation_score",
        ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
         (lit(m) / (col("rating_count") + lit(m))) * lit(C))
    )

    # ---------------------------------------------------------
    # Write to Movies Table
    # ---------------------------------------------------------
    print(f"\n[1/3] Writing to movies table...")

    movies_ready = movies_df.join(movie_stats, "movieId", "left") \
        .na.fill({"avg_rating": 0.0, "rating_count": 0})

    movies_to_db = movies_ready.select(
        col("movieId").alias("movie_id"),
        col("title"),
        col("genres"),
        col("avg_rating"),
        col("rating_count")
    ).withColumn("year", lit(None).cast("int")) \
     .withColumn("created_at", current_timestamp()) \
     .withColumn("updated_at", current_timestamp())

    movies_to_db.write.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "movies") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("append") \
        .save()

    print("   Movies table written successfully")

    # ---------------------------------------------------------
    # Read ID Mapping (Critical step for foreign key)
    # ---------------------------------------------------------
    print(f"\n[2/3] Reading ID mapping from database...")

    # Read only id and movie_id columns for mapping
    db_movies_df = spark.read.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "movies") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .load() \
        .select(col("id").alias("pk_id"), col("movie_id").alias("csv_id"))

    # Join recommendations with database IDs
    # recommendations.movieId = CSV movie ID
    # db_movies_df.csv_id = CSV movie ID
    # db_movies_df.pk_id = MySQL auto-increment primary key

    final_rec_data = recommendations.join(
        db_movies_df,
        recommendations.movieId == db_movies_df.csv_id,
        "inner"
    )

    rec_count = final_rec_data.count()
    print(f"   Mapped {rec_count} recommendations successfully")

    # ---------------------------------------------------------
    # Write to Recommendation Data Table
    # ---------------------------------------------------------
    print(f"\n[3/3] Writing to recommendation_data table...")

    rec_to_db = final_rec_data.select(
        col("pk_id").alias("movie_id"),  # Use database primary key for foreign key
        col("recommendation_score")
    ).withColumn("popularity_score", lit(0.0)) \
     .withColumn("genre_match_score", lit(0.0)) \
     .withColumn("user_id", lit(None).cast("int")) \
     .withColumn("created_at", current_timestamp()) \
     .withColumn("updated_at", current_timestamp())

    rec_to_db.write.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "recommendation_data") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("append") \
        .save()

    print("   Recommendation_data table written successfully")

    # Show top 10 recommendations
    print("\nTop 10 Recommendations:")
    print("-" * 70)
    top10 = final_rec_data.join(movies_df, final_rec_data.csv_id == movies_df.movieId) \
        .select("title", "recommendation_score") \
        .orderBy(desc("recommendation_score")) \
        .limit(10)
    top10.show(10, truncate=False)

    print("\n" + "=" * 70)
    print("Job completed successfully!")
    print("=" * 70)

except Exception as e:
    print(f"\nError occurred: {type(e).__name__}")
    print(f"Details: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

finally:
    if 'spark' in locals():
        spark.stop()
        print("\nSpark Session stopped")
