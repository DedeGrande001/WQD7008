"""
Spark 轻量测试 - 只处理少量数据验证流程
"""
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, lit, desc

print("=" * 70)
print("🧪 Spark 轻量测试 - 处理 100 条数据")
print("=" * 70)

# 数据库配置
RDS_HOST = "recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com"
RDS_DB = "recommendation_db"
RDS_USER = "admin"
RDS_PASSWORD = "RecommendDB2026!"
JDBC_URL = f"jdbc:mysql://{RDS_HOST}:3306/{RDS_DB}"

print(f"\n数据库: {RDS_HOST}/{RDS_DB}")

# 创建 Spark Session（限制资源）
print("\n📦 创建 Spark Session (limited resources)...")
spark = SparkSession.builder \
    .appName("MovieLens-Mini-Test") \
    .master("local[1]") \
    .config("spark.driver.memory", "512m") \
    .config("spark.executor.memory", "512m") \
    .config("spark.sql.shuffle.partitions", "2") \
    .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
print("✅ Spark Session 创建成功")

try:
    # 1. 读取 Movies (前100条)
    print("\n📂 读取 movies.csv (前100条)...")
    movies_full = spark.read.csv("data/movies.csv", header=True, inferSchema=True)
    movies_df = movies_full.limit(100)
    movies_count = movies_df.count()
    print(f"✅ 加载 {movies_count} 部电影")

    # 获取这些电影的 ID
    movie_ids = [row.movieId for row in movies_df.select("movieId").collect()]
    print(f"   电影ID范围: {min(movie_ids)} - {max(movie_ids)}")

    # 2. 读取 Ratings (只读取这100部电影的评分)
    print(f"\n📂 读取 ratings.csv (只读取这{movies_count}部电影的评分)...")
    ratings_full = spark.read.csv("data/ratings.csv", header=True, inferSchema=True)
    ratings_df = ratings_full.filter(col("movieId").isin(movie_ids))
    ratings_count = ratings_df.count()
    print(f"✅ 加载 {ratings_count} 条评分")

    # 3. 计算推荐数据
    print(f"\n🔢 计算推荐分数...")
    movie_stats = ratings_df.groupBy("movieId").agg(
        avg("rating").alias("avg_rating"),
        count("rating").alias("rating_count")
    )

    # 使用贝叶斯加权评分
    total_ratings = ratings_df.count()
    avg_rating_all = ratings_df.agg(avg("rating")).first()[0]
    m = 10  # 最小评分数阈值
    C = avg_rating_all  # 全局平均分

    print(f"   全局平均分: {C:.2f}")
    print(f"   总评分数: {total_ratings}")

    recommendations = movie_stats.withColumn(
        "recommendation_score",
        ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
         (lit(m) / (col("rating_count") + lit(m))) * lit(C))
    )

    rec_count = recommendations.count()
    print(f"✅ 生成 {rec_count} 条推荐")

    # 4. Join 电影信息
    print(f"\n🔗 合并电影信息...")
    final_data = recommendations.join(movies_df, "movieId", "inner") \
        .select(
            col("movieId").alias("movie_id"),
            col("title"),
            col("genres"),
            col("avg_rating"),
            col("rating_count"),
            col("recommendation_score")
        ) \
        .orderBy(desc("recommendation_score"))

    # 显示 Top 10
    print(f"\n🏆 Top 10 推荐:")
    final_data.show(10, truncate=False)

    # 5. 写入数据库
    print(f"\n💾 写入数据库...")

    # 写入 movies 表
    print(f"   写入 movies 表...")
    movies_to_db = movies_df.select(
        col("movieId").alias("movie_id"),
        col("title"),
        col("genres")
    )

    movies_to_db.write.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "movies") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("append") \
        .save()

    print(f"   ✅ {movies_count} 部电影已写入")

    # 写入 recommendation_data 表
    print(f"   写入 recommendation_data 表...")
    rec_to_db = final_data.select(
        col("movie_id"),
        col("recommendation_score")
    )

    rec_to_db.write.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "recommendation_data") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("append") \
        .save()

    print(f"   ✅ {rec_count} 条推荐已写入")

    print("\n" + "=" * 70)
    print("✅✅✅ 测试完成！数据已成功写入 RDS")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ 错误: {type(e).__name__}")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()

finally:
    spark.stop()
    print("\n🛑 Spark Session 已停止")
