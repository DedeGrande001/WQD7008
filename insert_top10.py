"""
直接用 SQL 插入前 10 条推荐数据
"""
import mysql.connector
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, lit, desc

print("=" * 70)
print("📝 插入 Top 10 推荐数据到数据库")
print("=" * 70)

# 数据库配置
RDS_HOST = "recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com"
RDS_DB = "recommendation_db"
RDS_USER = "admin"
RDS_PASSWORD = "RecommendDB2026!"

# 1. 用 Spark 计算推荐
print("\n📦 创建 Spark Session...")
spark = SparkSession.builder \
    .appName("Top10-Insert") \
    .master("local[1]") \
    .config("spark.driver.memory", "512m") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("\n📂 读取数据...")
movies_df = spark.read.csv("data/movies.csv", header=True, inferSchema=True).limit(100)
movie_ids = [row.movieId for row in movies_df.select("movieId").collect()]

ratings_df = spark.read.csv("data/ratings.csv", header=True, inferSchema=True) \
    .filter(col("movieId").isin(movie_ids))

print(f"✅ 加载 {movies_df.count()} 部电影, {ratings_df.count()} 条评分")

print("\n🔢 计算推荐分数...")
movie_stats = ratings_df.groupBy("movieId").agg(
    avg("rating").alias("avg_rating"),
    count("rating").alias("rating_count")
)

# 贝叶斯加权
m = 10
C = ratings_df.agg(avg("rating")).first()[0]

recommendations = movie_stats.withColumn(
    "recommendation_score",
    ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
     (lit(m) / (col("rating_count") + lit(m))) * lit(C))
)

final_data = recommendations.join(movies_df, "movieId", "inner") \
    .select(
        col("movieId").alias("movie_id"),
        col("title"),
        col("genres"),
        col("avg_rating"),
        col("rating_count"),
        col("recommendation_score")
    ) \
    .orderBy(desc("recommendation_score")) \
    .limit(10)

print("\n🏆 Top 10 推荐:")
final_data.show(10, truncate=False)

# 2. 收集数据到 Python
top10_list = final_data.collect()
spark.stop()

# 3. 连接数据库
print("\n💾 连接数据库...")
conn = mysql.connector.connect(
    host=RDS_HOST,
    user=RDS_USER,
    password=RDS_PASSWORD,
    database=RDS_DB
)
cursor = conn.cursor()

# 4. 插入数据
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

print(f"\n📝 插入 {len(top10_list)} 条数据...")

for row in top10_list:
    movie_id = int(row['movie_id'])
    title = row['title']
    genres = row['genres'] if row['genres'] else ''
    avg_rating = float(row['avg_rating'])
    rating_count = int(row['rating_count'])
    recommendation_score = float(row['recommendation_score'])

    # 提取年份（从标题中）
    import re
    year_match = re.search(r'\((\d{4})\)', title)
    year = int(year_match.group(1)) if year_match else 2000

    # 插入 movies 表
    insert_movie_sql = """
    INSERT INTO movies (movie_id, title, genres, year, avg_rating, rating_count, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    avg_rating = VALUES(avg_rating),
    rating_count = VALUES(rating_count),
    updated_at = VALUES(updated_at)
    """

    cursor.execute(insert_movie_sql, (
        movie_id, title, genres, year, avg_rating, rating_count, now, now
    ))

    # 插入 recommendation_data 表
    insert_rec_sql = """
    INSERT INTO recommendation_data
    (movie_id, recommendation_score, popularity_score, genre_match_score, user_id, created_at, updated_at)
    VALUES (
        (SELECT id FROM movies WHERE movie_id = %s),
        %s, %s, %s, %s, %s, %s
    )
    """

    # popularity_score 用 rating_count 归一化, genre_match_score 默认为 NULL
    popularity_score = min(rating_count / 100.0, 10.0)  # 归一化到 0-10

    cursor.execute(insert_rec_sql, (
        movie_id, recommendation_score, popularity_score, None, None, now, now
    ))

    print(f"   ✅ {title[:50]:<50} | 分数: {recommendation_score:.2f}")

conn.commit()
cursor.close()
conn.close()

print("\n" + "=" * 70)
print("✅✅✅ Top 10 推荐数据已成功写入数据库！")
print("=" * 70)

# 5. 验证
print("\n🔍 验证数据...")
conn = mysql.connector.connect(
    host=RDS_HOST,
    user=RDS_USER,
    password=RDS_PASSWORD,
    database=RDS_DB
)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM movies")
movie_count = cursor.fetchone()[0]
print(f"   Movies: {movie_count} 条")

cursor.execute("SELECT COUNT(*) FROM recommendation_data")
rec_count = cursor.fetchone()[0]
print(f"   Recommendations: {rec_count} 条")

cursor.close()
conn.close()
