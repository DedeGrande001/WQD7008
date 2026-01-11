"""
EMR Spark Job - Process MovieLens data and write to RDS
"""
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, regexp_extract, when, lit, desc
from pyspark.sql.types import IntegerType

# RDS 配置（从命令行参数获取）
if len(sys.argv) < 6:
    print("Usage: spark-submit emr_spark_job.py <s3_input> <rds_host> <rds_db> <rds_user> <rds_password>")
    sys.exit(1)

S3_INPUT = sys.argv[1]  # s3://bucket/input/
RDS_HOST = sys.argv[2]
RDS_DB = sys.argv[3]
RDS_USER = sys.argv[4]
RDS_PASSWORD = sys.argv[5]

JDBC_URL = f"jdbc:mysql://{RDS_HOST}:3306/{RDS_DB}"

print(f"Starting Spark job...")
print(f"S3 Input: {S3_INPUT}")
print(f"RDS Host: {RDS_HOST}")

# 创建 Spark Session
spark = SparkSession.builder \
    .appName("MovieLens-Recommendation-EMR") \
    .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33,org.apache.hadoop:hadoop-aws:3.3.2,com.amazonaws:aws-java-sdk-bundle:1.11.1026") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("✅ Spark session created")

# 1. 读取数据
print("\n📂 Reading movies from S3...")
movies_df = spark.read.csv(
    f"{S3_INPUT}/movies.csv",
    header=True,
    inferSchema=True
)
print(f"✅ Loaded {movies_df.count():,} movies")

print("\n📂 Reading ratings from S3...")
ratings_df = spark.read.csv(
    f"{S3_INPUT}/ratings.csv",
    header=True,
    inferSchema=True
)
print(f"✅ Loaded {ratings_df.count():,} ratings")

# 2. 提取年份
print("\n📊 Processing data...")
movies_df = movies_df.withColumn(
    "year",
    when(
        regexp_extract(col("title"), r"\((\d{4})\)", 1) != "",
        regexp_extract(col("title"), r"\((\d{4})\)", 1).cast(IntegerType())
    ).otherwise(None)
)

# 3. 计算评分统计
rating_stats = ratings_df.groupBy("movieId").agg(
    avg("rating").alias("avg_rating"),
    count("rating").alias("rating_count")
)

# 4. 过滤并生成推荐
MIN_RATINGS = 100
qualified_movies = rating_stats.filter(col("rating_count") >= MIN_RATINGS)
print(f"✅ Found {qualified_movies.count():,} qualified movies")

recommendations = qualified_movies.join(movies_df, on="movieId", how="inner")

# 5. 计算 Bayesian 加权评分
global_stats = rating_stats.agg(
    avg("avg_rating").alias("global_avg")
).collect()[0]

C = global_stats["global_avg"]
m = MIN_RATINGS

recommendations = recommendations.withColumn(
    "recommendation_score",
    ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
     (lit(m) / (col("rating_count") + lit(m))) * lit(C))
).withColumn(
    "popularity_score",
    col("rating_count")
)

# 6. 准备写入数据库的数据
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

print(f"\n✅ Generated {db_data.count():,} recommendations")
print("\n🎬 Top 10 Recommendations:")
db_data.orderBy(desc("recommendation_score")).select("title", "recommendation_score").show(10, False)

# 7. 写入 RDS
print(f"\n📊 Writing to RDS: {RDS_HOST}/{RDS_DB}...")

# 写入数据（使用 overwrite 模式清空旧数据）
db_data.write \
    .format("jdbc") \
    .option("url", JDBC_URL) \
    .option("dbtable", "movies") \
    .option("user", RDS_USER) \
    .option("password", RDS_PASSWORD) \
    .option("driver", "com.mysql.cj.jdbc.Driver") \
    .mode("overwrite") \
    .save()

print("✅ Data written to RDS successfully!")

print("\n" + "="*70)
print("✅ JOB COMPLETED SUCCESSFULLY!")
print("="*70)

spark.stop()
