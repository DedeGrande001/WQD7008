"""
测试从 S3 读取数据的脚本
用于在本地调试 Spark S3 配置
"""
import os
from pyspark.sql import SparkSession

print("=" * 60)
print("测试 Spark 读取 S3 数据")
print("=" * 60)

# S3 路径
S3_BUCKET = "s3a://recommendation-system-data-dedegrande/input"

print(f"\n尝试读取: {S3_BUCKET}/movies.csv")

# 尝试方案 1: 基础配置
print("\n方案 1: 使用 Hadoop AWS 3.3.2 + AWS SDK 1.11.1026")
try:
    spark = SparkSession.builder \
        .appName("S3-Test") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.2,com.amazonaws:aws-java-sdk-bundle:1.11.1026") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    print("✅ Spark session 创建成功")

    # 尝试读取
    print(f"📂 读取 movies.csv...")
    movies_df = spark.read.csv(
        f"{S3_BUCKET}/movies.csv",
        header=True,
        inferSchema=True
    )

    count = movies_df.count()
    print(f"✅ 成功读取 {count} 条电影记录")

    # 显示前几行
    print("\n前 5 条记录:")
    movies_df.show(5, truncate=False)

    spark.stop()
    print("\n✅✅✅ 方案 1 成功！")

except Exception as e:
    print(f"\n❌ 方案 1 失败: {type(e).__name__}")
    print(f"错误: {str(e)[:200]}")
    try:
        spark.stop()
    except:
        pass

print("\n" + "=" * 60)
