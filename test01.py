"""
Spark 轻量测试 - 修正版
解决数据库字段缺失 (Field doesn't have a default value) 问题
"""
import os
import traceback
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, lit, desc, current_timestamp, when

print("=" * 70)
print("🧪 Spark 轻量测试 (Fix Version) - 处理 100 条数据")
print("=" * 70)

# ---------------------------------------------------------
# 1. 配置部分
# ---------------------------------------------------------
RDS_HOST = "recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com"
RDS_DB = "recommendation_db"
RDS_USER = "admin"
RDS_PASSWORD = "RecommendDB2026!"
JDBC_URL = f"jdbc:mysql://{RDS_HOST}:3306/{RDS_DB}?useSSL=false&allowPublicKeyRetrieval=true"

print(f"\n数据库: {RDS_HOST}/{RDS_DB}")

# 创建 Spark Session
print("\n📦 创建 Spark Session (limited resources)...")
spark = SparkSession.builder \
    .appName("MovieLens-Mini-Test-Fix") \
    .master("local[1]") \
    .config("spark.driver.memory", "512m") \
    .config("spark.executor.memory", "512m") \
    .config("spark.sql.shuffle.partitions", "2") \
    # 确保包含 mysql 驱动
    .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
print("✅ Spark Session 创建成功")

try:
    # ---------------------------------------------------------
    # 2. 读取数据 & 计算
    # ---------------------------------------------------------
    
    # 读取 Movies (前100条)
    print("\n📂 读取 movies.csv (前100条)...")
    movies_full = spark.read.csv("data/movies.csv", header=True, inferSchema=True)
    movies_df = movies_full.limit(100)
    
    # 获取这些电影的 ID 用于过滤评分
    movie_ids = [row.movieId for row in movies_df.select("movieId").collect()]
    print(f"   已加载 {len(movie_ids)} 部电影")

    # 读取 Ratings
    print(f"\n📂 读取 ratings.csv (关联评分)...")
    ratings_full = spark.read.csv("data/ratings.csv", header=True, inferSchema=True)
    ratings_df = ratings_full.filter(col("movieId").isin(movie_ids))
    print(f"   已加载 {ratings_df.count()} 条评分")

    # 计算统计数据 (Avg, Count)
    print(f"\n🔢 计算推荐分数...")
    movie_stats = ratings_df.groupBy("movieId").agg(
        avg("rating").alias("avg_rating"),
        count("rating").alias("rating_count")
    )

    # 贝叶斯加权计算
    avg_rating_all = ratings_df.agg(avg("rating")).first()[0] or 3.0 # 防止为空给个默认值
    m = 10
    C = avg_rating_all

    # 生成推荐分数表
    recommendations = movie_stats.withColumn(
        "recommendation_score",
        ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
         (lit(m) / (col("rating_count") + lit(m))) * lit(C))
    )

    # ---------------------------------------------------------
    # 3. 准备写入 Movies 表 (关键修改)
    # ---------------------------------------------------------
    print(f"\n💾 正在写入数据库...")

    # A. 准备 Movies 数据：需要合并统计信息，并补全数据库必填字段
    print(f"   [1/2] 写入 movies 表...")
    
    # 关联 movies_df 和 movie_stats，如果没有评分，填充默认值
    movies_ready = movies_df.join(movie_stats, "movieId", "left") \
        .na.fill({"avg_rating": 0.0, "rating_count": 0})

    # 构造符合数据库 schema 的 DataFrame
    movies_to_db = movies_ready.select(
        col("movieId").alias("movie_id"),      # 对应数据库 movie_id
        col("title"),                          # 对应数据库 title
        col("genres"),                         # 对应数据库 genres
        col("avg_rating"),                     # ✅ 补全: 数据库必填
        col("rating_count")                    # ✅ 补全: 数据库必填
    ).withColumn("year", lit(None).cast("int")) \
     .withColumn("created_at", current_timestamp()) \
     .withColumn("updated_at", current_timestamp())

    # 写入 movies
    movies_to_db.write.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "movies") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("append") \
        .save()
    
    print(f"   ✅ movies 表写入成功")

    # ---------------------------------------------------------
    # 4. 准备写入 Recommendation Data 表 (关键修改)
    # ---------------------------------------------------------
    print(f"   [2/2] 写入 recommendation_data 表...")

    # B. 准备 Recommendation 数据：补全 popularity, score, timestamps 等
    # 注意：这里我们直接 Join 前面算好的 recommendations
    
    rec_to_db = recommendations.select(
        col("movieId").alias("movie_id"),        # 对应数据库 movie_id (注意外键逻辑)
        col("recommendation_score")              # 对应数据库 recommendation_score
    ).withColumn("popularity_score", lit(0.0)) \
     .withColumn("genre_match_score", lit(0.0)) \
     .withColumn("user_id", lit(None).cast("int")) \
     .withColumn("created_at", current_timestamp()) \
     .withColumn("updated_at", current_timestamp())

    # 写入 recommendation_data
    rec_to_db.write.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "recommendation_data") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("append") \
        .save()

    print(f"   ✅ recommendation_data 表写入成功")

    print("\n" + "=" * 70)
    print("🎉🎉🎉 测试完成！所有数据已成功写入 RDS")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ 发生错误: {type(e).__name__}")
    print(f"   详细信息: {str(e)}")
    print("-" * 30)
    traceback.print_exc()

finally:
    if 'spark' in locals():
        spark.stop()
        print("\n🛑 Spark Session 已停止")