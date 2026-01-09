"""
AWS EMR Spark Job for MovieLens Recommendation Processing
Reads data from S3, processes with Spark, writes to RDS MySQL
"""
import sys
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, regexp_extract, when, lit, desc
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType, LongType


class MovieLensSparkEMR:
    def __init__(self, s3_bucket, db_config):
        """Initialize Spark session for EMR"""
        self.s3_bucket = s3_bucket
        self.db_config = db_config

        # Create Spark session
        self.spark = SparkSession.builder \
            .appName("MovieLens-EMR-Processing") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .config("spark.executor.memory", "4g") \
            .config("spark.executor.cores", "2") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

        print(f"\n{'='*70}")
        print(f"🚀 MovieLens Spark Processing on AWS EMR")
        print(f"{'='*70}")
        print(f"Spark Version: {self.spark.version}")
        print(f"S3 Bucket: {self.s3_bucket}")
        print(f"Database Host: {self.db_config['host']}")
        print(f"{'='*70}\n")

    def process_movielens(self, min_ratings=50, top_n=1000):
        """
        Process MovieLens data from S3

        Args:
            min_ratings: Minimum number of ratings for a movie to be recommended
            top_n: Number of top recommendations to generate
        """

        # S3 paths
        movies_path = f"s3://{self.s3_bucket}/input/movies.csv"
        ratings_path = f"s3://{self.s3_bucket}/input/ratings.csv"

        # 1. Read movies from S3
        print(f"📂 Reading movies from S3: {movies_path}")
        movies_schema = StructType([
            StructField("movieId", IntegerType(), True),
            StructField("title", StringType(), True),
            StructField("genres", StringType(), True)
        ])
        movies_df = self.spark.read.csv(
            movies_path,
            header=True,
            schema=movies_schema
        )

        # Extract year from title
        movies_df = movies_df.withColumn(
            "year",
            when(
                regexp_extract(col("title"), r"\((\d{4})\)", 1) != "",
                regexp_extract(col("title"), r"\((\d{4})\)", 1).cast(IntegerType())
            ).otherwise(None)
        )

        movies_count = movies_df.count()
        print(f"✅ Loaded {movies_count:,} movies")

        # 2. Read ratings from S3
        print(f"📂 Reading ratings from S3: {ratings_path}")
        ratings_schema = StructType([
            StructField("userId", IntegerType(), True),
            StructField("movieId", IntegerType(), True),
            StructField("rating", FloatType(), True),
            StructField("timestamp", LongType(), True)
        ])
        ratings_df = self.spark.read.csv(
            ratings_path,
            header=True,
            schema=ratings_schema
        )

        ratings_count = ratings_df.count()
        print(f"✅ Loaded {ratings_count:,} ratings")

        # 3. Calculate statistics (parallel aggregation)
        print(f"\n📊 Calculating movie statistics (distributed)...")
        stats_df = ratings_df.groupBy("movieId").agg(
            avg("rating").alias("avg_rating"),
            count("rating").alias("rating_count")
        )

        stats_count = stats_df.count()
        print(f"✅ Calculated statistics for {stats_count:,} movies")

        # 4. Join movies with statistics
        print(f"🔗 Joining movies with statistics...")
        movies_with_stats = movies_df.join(stats_df, "movieId", "left") \
            .fillna({"avg_rating": 0.0, "rating_count": 0})

        # 5. Generate recommendations
        print(f"\n⭐ Generating top-rated movies...")
        print(f"   Minimum ratings threshold: {min_ratings}")
        print(f"   Top N movies: {top_n}")

        # Filter by minimum rating count
        filtered = movies_with_stats.filter(col("rating_count") >= min_ratings)

        # Calculate weighted rating (Bayesian average)
        mean_rating = stats_df.agg(avg("avg_rating")).collect()[0][0]
        print(f"   Global mean rating: {mean_rating:.2f}")

        filtered = filtered.withColumn(
            "weighted_rating",
            ((col("rating_count") / (col("rating_count") + lit(min_ratings))) * col("avg_rating") +
             (lit(min_ratings) / (col("rating_count") + lit(min_ratings))) * lit(mean_rating))
        )

        # Get top N movies
        top_movies = filtered.orderBy(desc("weighted_rating")).limit(top_n)
        top_count = top_movies.count()
        print(f"✅ Generated {top_count:,} recommendations")

        # Show sample
        print(f"\n📋 Top 10 Recommendations:")
        top_movies.select("title", "genres", "avg_rating", "rating_count", "weighted_rating") \
            .show(10, truncate=False)

        # 6. Save to RDS MySQL
        print(f"\n💾 Saving data to RDS MySQL...")
        self._save_to_mysql(movies_with_stats, top_movies)

        print(f"\n{'='*70}")
        print("✅ PROCESSING COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
        print(f"\n📊 Summary:")
        print(f"   Total movies: {movies_count:,}")
        print(f"   Total ratings: {ratings_count:,}")
        print(f"   Movies with stats: {stats_count:,}")
        print(f"   Recommendations generated: {top_count:,}")
        print(f"\n🌐 View results at your Django web interface")
        print()

    def _save_to_mysql(self, movies_df, recommendations_df):
        """
        Save DataFrames to MySQL using JDBC

        Args:
            movies_df: Movies with statistics DataFrame
            recommendations_df: Top recommendations DataFrame
        """

        # JDBC connection properties
        jdbc_url = f"jdbc:mysql://{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        connection_properties = {
            "user": self.db_config['user'],
            "password": self.db_config['password'],
            "driver": "com.mysql.jdbc.Driver"
        }

        # Prepare movies data
        print(f"   Preparing movies data for database...")
        movies_for_db = movies_df.select(
            col("movieId").alias("movie_id"),
            col("title"),
            col("genres"),
            col("year"),
            col("avg_rating"),
            col("rating_count").cast(IntegerType())
        )

        # Save movies (overwrite existing data)
        print(f"   Writing {movies_for_db.count():,} movies to database...")
        movies_for_db.write \
            .jdbc(
                url=jdbc_url,
                table="app_movie",
                mode="overwrite",
                properties=connection_properties
            )
        print(f"   ✅ Movies saved successfully")

        # Prepare recommendations data
        print(f"   Preparing recommendations data for database...")

        # First, create a mapping of movieId to movie primary key (id)
        # This is a simplified approach - in production, you'd query existing IDs
        recommendations_for_db = recommendations_df.select(
            col("movieId").alias("movie_id_ref"),
            col("weighted_rating").alias("recommendation_score"),
            col("avg_rating").alias("popularity_score"),
            lit(0.0).alias("genre_match_score")  # Placeholder
        )

        # Save recommendations (overwrite existing data)
        print(f"   Writing {recommendations_for_db.count():,} recommendations to database...")
        recommendations_for_db.write \
            .jdbc(
                url=jdbc_url,
                table="app_recommendationdata",
                mode="overwrite",
                properties=connection_properties
            )
        print(f"   ✅ Recommendations saved successfully")

    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("\n🛑 Spark session stopped\n")


def main():
    """Main execution"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MovieLens Spark EMR Processing')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket name')
    parser.add_argument('--db-host', required=True, help='RDS MySQL host')
    parser.add_argument('--db-name', required=True, help='Database name')
    parser.add_argument('--db-user', required=True, help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    parser.add_argument('--db-port', default='3306', help='Database port')
    parser.add_argument('--min-ratings', type=int, default=50, help='Minimum ratings threshold')
    parser.add_argument('--top-n', type=int, default=1000, help='Number of top recommendations')

    args = parser.parse_args()

    # Database configuration
    db_config = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }

    # Create processor
    processor = MovieLensSparkEMR(
        s3_bucket=args.s3_bucket,
        db_config=db_config
    )

    try:
        # Process data
        processor.process_movielens(
            min_ratings=args.min_ratings,
            top_n=args.top_n
        )
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        processor.stop()


if __name__ == "__main__":
    main()
