"""
Spark 轻量测试 - 最终修正版
解决 Foreign Key 报错：加入“回读 ID”逻辑
"""
import os
import traceback
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, lit, desc, current_timestamp

print("=" * 70)
print("🧪 Spark 轻量测试 (Final Fix) - 处理 100 条数据")
print("=" * 70)

# ---------------------------------------------------------
# 1. 配置部分
# ---------------------------------------------------------
RDS_HOST = "recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com"
RDS_DB = "recommendation_db"
RDS_USER = "admin"
RDS_PASSWORD = "RecommendDB2026!"
# 必须允许公钥检索，否则有些版本连不上
JDBC_URL = f"jdbc:mysql://{RDS_HOST}:3306/{RDS_DB}?useSSL=false&allowPublicKeyRetrieval=true"

print(f"\n数据库: {RDS_HOST}/{RDS_DB}")

print("\n📦 创建 Spark Session...")
spark = SparkSession.builder \
    .appName("MovieLens-Mini-Test-Final") \
    .master("local[1]") \
    .config("spark.driver.memory", "512m") \
    .config("spark.executor.memory", "512m") \
    .config("spark.sql.shuffle.partitions", "2") \
    .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
print("✅ Spark Session 创建成功")

try:
    # ---------------------------------------------------------
    # 2. 读取数据 & 计算
    # ---------------------------------------------------------
    print("\n📂 读取数据并计算...")
    
    # 读取 Movies (前100条)
    movies_full = spark.read.csv("data/movies.csv", header=True, inferSchema=True)
    movies_df = movies_full.limit(100)
    
    # 提取 ID 列表
    movie_ids = [row.movieId for row in movies_df.select("movieId").collect()]
    
    # 读取 Ratings
    ratings_full = spark.read.csv("data/ratings.csv", header=True, inferSchema=True)
    ratings_df = ratings_full.filter(col("movieId").isin(movie_ids))

    # 计算统计
    movie_stats = ratings_df.groupBy("movieId").agg(
        avg("rating").alias("avg_rating"),
        count("rating").alias("rating_count")
    )

    # 贝叶斯平均
    avg_rating_all = ratings_df.agg(avg("rating")).first()[0] or 3.0
    m = 10
    C = avg_rating_all

    recommendations = movie_stats.withColumn(
        "recommendation_score",
        ((col("rating_count") / (col("rating_count") + lit(m))) * col("avg_rating") +
         (lit(m) / (col("rating_count") + lit(m))) * lit(C))
    )

    # ---------------------------------------------------------
    # 3. 写入 Movies 表
    # ---------------------------------------------------------
    print(f"\n💾 [1/3] 写入 movies 表...")
    
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

    # 这里的 append 模式会保留之前写入的重复数据，测试没关系
    # 生产环境通常需要做 upsert，但这里保持简单
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
    # 4. 回读 ID 映射 (解决外键问题的关键步骤)
    # ---------------------------------------------------------
    print(f"\n🔄 [2/3] 从数据库回读 ID 映射...")
    
    # 我们只读 id 和 movie_id 两列，用来做字典映射
    db_movies_df = spark.read.format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "movies") \
        .option("user", RDS_USER) \
        .option("password", RDS_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .load() \
        .select(col("id").alias("pk_id"), col("movie_id").alias("csv_id"))

    # 将推荐结果 (含 csv_id) 与 数据库映射 (csv_id -> pk_id) 进行 Join
    # recommendations.movieId 是 CSV 里的 ID
    # db_movies_df.csv_id 也是 CSV 里的 ID
    # db_movies_df.pk_id 是 MySQL 生成的主键 ID (我们要写入外键的值)
    
    final_rec_data = recommendations.join(
        db_movies_df, 
        recommendations.movieId == db_movies_df.csv_id, 
        "inner"
    )
    
    print(f"   ✅ 映射成功，准备写入 {final_rec_data.count()} 条推荐数据")

    # ---------------------------------------------------------
    # 5. 写入 Recommendation Data 表
    # ---------------------------------------------------------
    print(f"\n💾 [3/3] 写入 recommendation_data 表...")

    rec_to_db = final_rec_data.select(
        col("pk_id").alias("movie_id"),          # ⚠️ 注意：这里用的是数据库的主键 ID！
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

    print(f"   ✅ recommendation_data 表写入成功")

    print("\n" + "=" * 70)
    print("🎉🎉🎉 全部完成！数据逻辑已修复。")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ 发生错误: {type(e).__name__}")
    print(f"   详细信息: {str(e)}")
    # 打印简短的错误链，方便调试
    traceback.print_exc()

finally:
    if 'spark' in locals():
        spark.stop()
        print("\n🛑 Spark Session 已停止")