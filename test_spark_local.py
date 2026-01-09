"""
Local Spark test script - Test MovieLens processing locally
"""
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, regexp_extract, when, lit, desc
from pyspark.sql.types import StructType, StructField, StringType, FloatType, IntegerType, LongType

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

class LocalSparkTest:
    def __init__(self):
        """Initialize local Spark session"""
        print("Initializing local Spark session...")

        self.spark = SparkSession.builder \
            .appName("MovieLens-Local-Test") \
            .master("local[*]") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

        print(f"✅ Spark {self.spark.version} initialized")
        print()

    def test_read_csv(self):
        """Test reading CSV files"""
        print("="*70)
        print("TEST 1: Reading CSV Files")
        print("="*70)

        # Read movies
        movies_path = "data/movies.csv"
        print(f"📂 Reading: {movies_path}")

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

        movies_count = movies_df.count()
        print(f"✅ Loaded {movies_count:,} movies")
        print("\nSample movies:")
        movies_df.show(5, truncate=False)

        # Read ratings
        ratings_path = "data/ratings.csv"
        print(f"\n📂 Reading: {ratings_path}")

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
        print("\nSample ratings:")
        ratings_df.show(5)

        return movies_df, ratings_df

    def test_data_processing(self, movies_df, ratings_df):
        """Test data processing logic"""
        print("\n" + "="*70)
        print("TEST 2: Data Processing")
        print("="*70)

        # Extract year from title
        print("📊 Extracting year from movie titles...")
        movies_df = movies_df.withColumn(
            "year",
            when(
                regexp_extract(col("title"), r"\((\d{4})\)", 1) != "",
                regexp_extract(col("title"), r"\((\d{4})\)", 1).cast(IntegerType())
            ).otherwise(None)
        )

        print("✅ Year extraction complete")
        print("\nMovies with years:")
        movies_df.select("title", "year", "genres").show(5, truncate=False)

        # Calculate rating statistics
        print("\n📊 Calculating rating statistics...")
        rating_stats = ratings_df.groupBy("movieId").agg(
            avg("rating").alias("avg_rating"),
            count("rating").alias("rating_count")
        )

        print("✅ Statistics calculated")
        print("\nTop rated movies (by count):")
        rating_stats.orderBy(desc("rating_count")).show(10)

        return movies_df, rating_stats

    def test_recommendation_generation(self, movies_df, rating_stats, min_ratings=50):
        """Test recommendation score calculation"""
        print("\n" + "="*70)
        print("TEST 3: Generating Recommendations")
        print("="*70)

        # Filter movies with minimum ratings
        print(f"📊 Filtering movies with at least {min_ratings} ratings...")
        qualified_movies = rating_stats.filter(col("rating_count") >= min_ratings)
        qualified_count = qualified_movies.count()
        print(f"✅ Found {qualified_count:,} qualified movies")

        # Join with movie info
        recommendations = qualified_movies.join(
            movies_df,
            on="movieId",
            how="inner"
        )

        # Calculate Bayesian weighted rating
        print("\n📊 Calculating Bayesian weighted ratings...")

        # Get global statistics
        global_stats = rating_stats.agg(
            avg("avg_rating").alias("global_avg"),
            avg("rating_count").alias("global_count")
        ).collect()[0]

        C = global_stats["global_avg"]  # Global average rating
        m = min_ratings  # Minimum votes

        print(f"   Global average rating: {C:.2f}")
        print(f"   Minimum ratings threshold: {m}")

        # Bayesian formula: (v/(v+m)) * R + (m/(v+m)) * C
        recommendations = recommendations.withColumn(
            "recommendation_score",
            ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
             (lit(m) / (col("rating_count") + lit(m))) * lit(C))
        )

        recommendations = recommendations.withColumn(
            "popularity_score",
            col("rating_count")
        )

        print("✅ Recommendation scores calculated")

        # Show top recommendations
        print("\n🎬 Top 20 Recommendations:")
        top_recommendations = recommendations.orderBy(
            desc("recommendation_score"),
            desc("rating_count")
        ).select(
            "title",
            "genres",
            "year",
            "avg_rating",
            "rating_count",
            "recommendation_score"
        ).limit(20)

        top_recommendations.show(20, truncate=False)

        return recommendations

    def test_database_write(self, recommendations):
        """Test writing to SQLite database"""
        print("\n" + "="*70)
        print("TEST 4: Writing to Database")
        print("="*70)

        # Prepare data for database
        print("📊 Preparing data for database...")

        # Select and rename columns to match Django models
        db_data = recommendations.select(
            col("movieId").alias("movie_id"),
            col("title"),
            col("genres"),
            col("year"),
            col("avg_rating"),
            col("rating_count"),
            col("recommendation_score"),
            col("popularity_score")
        )

        # Convert to Pandas (for SQLite insertion)
        print("📊 Converting to Pandas DataFrame...")
        pandas_df = db_data.toPandas()

        print(f"✅ Prepared {len(pandas_df):,} recommendations")
        print("\nFirst 10 records:")
        print(pandas_df.head(10).to_string())

        # Try to write to SQLite
        try:
            import sqlite3
            from datetime import datetime

            db_path = "db.sqlite3"
            print(f"\n📊 Writing to SQLite: {db_path}")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if movies table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='movies'")
            if not cursor.fetchone():
                print("⚠️  Database tables not found. Run 'python manage.py migrate' first!")
                conn.close()
                return False

            # Clear existing data
            cursor.execute("DELETE FROM recommendation_data")
            cursor.execute("DELETE FROM movies")
            conn.commit()

            # Insert movies
            inserted_movies = 0
            for _, row in pandas_df.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO movies (movie_id, title, genres, year, avg_rating, rating_count, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        int(row['movie_id']),
                        str(row['title']),
                        str(row['genres']) if row['genres'] else '',
                        int(row['year']) if row['year'] else None,
                        float(row['avg_rating']),
                        int(row['rating_count']),
                        datetime.now(),
                        datetime.now()
                    ))

                    # Get the movie's database ID
                    movie_db_id = cursor.lastrowid

                    # Insert recommendation
                    cursor.execute("""
                        INSERT INTO recommendation_data (movie_id, recommendation_score, popularity_score, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        movie_db_id,
                        float(row['recommendation_score']),
                        float(row['popularity_score']),
                        datetime.now(),
                        datetime.now()
                    ))

                    inserted_movies += 1

                except Exception as e:
                    print(f"⚠️  Error inserting movie {row['movie_id']}: {e}")
                    continue

            conn.commit()
            conn.close()

            print(f"✅ Successfully inserted {inserted_movies:,} movies and recommendations")
            return True

        except Exception as e:
            print(f"❌ Database write failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("🧪 RUNNING ALL SPARK TESTS")
        print("="*70)
        print()

        try:
            # Test 1: Read CSV
            movies_df, ratings_df = self.test_read_csv()

            # Test 2: Process data
            movies_df, rating_stats = self.test_data_processing(movies_df, ratings_df)

            # Test 3: Generate recommendations
            recommendations = self.test_recommendation_generation(movies_df, rating_stats, min_ratings=100)

            # Test 4: Write to database
            success = self.test_database_write(recommendations)

            print("\n" + "="*70)
            if success:
                print("✅ ALL TESTS PASSED!")
            else:
                print("⚠️  TESTS COMPLETED WITH WARNINGS")
            print("="*70)
            print()

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.spark.stop()
            print("✅ Spark session stopped")


if __name__ == "__main__":
    tester = LocalSparkTest()
    tester.run_all_tests()
