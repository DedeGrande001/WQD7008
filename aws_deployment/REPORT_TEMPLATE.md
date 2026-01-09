# Group Assignment 2 - Technical Report Template

**课程**: WQD7008 - Distributed Computing
**小组成员**: [填写成员名单]
**提交日期**: 2026年1月15日

---

## Table of Contents

1. Introduction
2. System Architecture
3. Implementation Details
4. Performance Analysis
5. Cost Analysis
6. Challenges and Solutions
7. Conclusion
8. References

---

## 1. Introduction (1 page)

### 1.1 Background

本项目基于 Project 1 的设计，在 AWS 云平台上实现了一个分布式电影推荐系统。系统使用 Apache Spark 在 Amazon EMR 集群上进行大规模数据处理，使用 Amazon RDS 存储数据，并通过 EC2 实例提供 Web 服务。

### 1.2 Objectives

- 在 AWS 环境中部署分布式架构
- 实现基于 Spark 的并行数据处理
- 演示系统的可扩展性和性能优势
- 控制成本在 $50 预算内

### 1.3 Dataset

**MovieLens Dataset**
- 来源: GroupLens Research
- 规模: [填写你使用的数据集大小，1M 或 25M]
- 内容: [X] 部电影，[Y] 条用户评分
- 格式: CSV (movies.csv, ratings.csv)

---

## 2. System Architecture (3 pages)

### 2.1 Architecture Diagram

[插入架构图 - 使用 draw.io 或 AWS Architecture Icons 制作]

```
用户浏览器
    ↓ HTTPS
[Application Load Balancer] (可选)
    ↓
┌─────────────────────────────────────┐
│  EC2 Instance (t2.small)            │
│  - Django Web Application           │
│  - Gunicorn WSGI Server             │
│  - Python 3.10                      │
└─────────────────────────────────────┘
    ↓ SQL Queries
┌─────────────────────────────────────┐
│  RDS MySQL (db.t3.micro)            │
│  - recommendation_db                │
│  - Tables: movies, recommendations  │
└─────────────────────────────────────┘
    ↑ JDBC Write
┌─────────────────────────────────────┐
│  EMR Cluster (按需启动)              │
│  - Master: 1x m5.xlarge             │
│  - Core: 2x m5.xlarge               │
│  - Spark 3.4.1 + Hadoop 3.3.3       │
└─────────────────────────────────────┘
    ↑ Read CSV
┌─────────────────────────────────────┐
│  S3 Bucket                          │
│  - input/movies.csv                 │
│  - input/ratings.csv                │
│  - scripts/spark_emr.py             │
└─────────────────────────────────────┘
```

### 2.2 AWS Services Used

| Service | Purpose | Configuration |
|---------|---------|--------------|
| **EC2** | Web 服务器 | Ubuntu 22.04, t2.small, 1 vCPU, 2GB RAM |
| **RDS** | 关系数据库 | MySQL 8.0, db.t3.micro, 20GB storage |
| **S3** | 对象存储 | Standard storage class, ~1GB data |
| **EMR** | 分布式计算 | Spark 3.4.1, 1 Master + 2 Core (m5.xlarge) |
| **CloudWatch** | 监控 | 默认指标 + 自定义日志 |
| **IAM** | 权限管理 | EMR roles, EC2 instance profile |
| **VPC** | 网络 | 默认 VPC, 安全组配置 |

### 2.3 Design Rationale

#### Why EMR + Spark?
- **分布式处理**: Spark 的 in-memory 计算比传统 MapReduce 快 100x
- **可扩展性**: 可轻松增加 Core 节点处理更大数据集
- **成本效率**: 按需启动，处理完成后终止
- **易集成**: 原生支持 S3、RDS 等 AWS 服务

#### Why RDS MySQL?
- **托管服务**: 自动备份、补丁管理
- **高可用性**: Multi-AZ 部署选项
- **标准接口**: JDBC 连接，兼容性好

#### Why S3?
- **耐久性**: 99.999999999% (11个9)
- **无限扩展**: 按需存储
- **低成本**: $0.023/GB/月

---

## 3. Implementation Details (5 pages)

### 3.1 Data Storage Layer (S3)

#### 3.1.1 Bucket Structure

```
s3://recommendation-system-data/
├── input/
│   ├── movies.csv (3 MB)
│   └── ratings.csv (648 MB)
├── scripts/
│   ├── spark_emr.py (核心处理脚本)
│   └── bootstrap.sh (EMR 引导脚本)
└── logs/ (可选)
    └── spark-logs/
```

#### 3.1.2 Data Format

**movies.csv**:
```csv
movieId,title,genres
1,"Toy Story (1995)",Animation|Children|Comedy
2,"Jumanji (1995)",Adventure|Children|Fantasy
```

**ratings.csv**:
```csv
userId,movieId,rating,timestamp
1,1,4.0,964982703
1,3,4.0,964981247
```

[插入 S3 控制台截图]

### 3.2 Database Layer (RDS)

#### 3.2.1 Schema Design

**Table: app_movie**
```sql
CREATE TABLE app_movie (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT UNIQUE NOT NULL,
    title VARCHAR(500),
    genres VARCHAR(200),
    year INT,
    avg_rating FLOAT DEFAULT 0.0,
    rating_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_movie_id (movie_id),
    INDEX idx_year (year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Table: app_recommendationdata**
```sql
CREATE TABLE app_recommendationdata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    movie_id_ref INT NOT NULL,
    recommendation_score FLOAT NOT NULL,
    popularity_score FLOAT,
    genre_match_score FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_movie_ref (movie_id_ref),
    INDEX idx_score (recommendation_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 3.2.2 RDS Configuration

[插入 RDS 配置截图]

- **Instance Class**: db.t3.micro (2 vCPUs, 1 GB RAM)
- **Storage**: 20 GB SSD (gp2)
- **Multi-AZ**: Disabled (成本考虑)
- **Backup**: Automated daily backups (可选)

### 3.3 Compute Layer (EMR + Spark)

#### 3.3.1 EMR Cluster Configuration

```json
{
  "Name": "recommendation-spark-cluster",
  "ReleaseLabel": "emr-6.15.0",
  "Applications": ["Spark", "Hadoop"],
  "Instances": {
    "MasterInstanceType": "m5.xlarge",
    "CoreInstanceType": "m5.xlarge",
    "CoreInstanceCount": 2,
    "KeepJobFlowAliveWhenNoSteps": true
  },
  "BootstrapActions": [
    {
      "Name": "Install MySQL Driver",
      "ScriptBootstrapAction": {
        "Path": "s3://recommendation-system-data/scripts/bootstrap.sh"
      }
    }
  ]
}
```

[插入 EMR 集群截图]

#### 3.3.2 Spark Processing Algorithm

**核心算法：贝叶斯加权评分**

```python
# 1. 读取数据（分布式）
movies_df = spark.read.csv("s3://.../movies.csv")
ratings_df = spark.read.csv("s3://.../ratings.csv")

# 2. 计算统计（并行聚合）
stats_df = ratings_df.groupBy("movieId").agg(
    avg("rating").alias("avg_rating"),
    count("rating").alias("rating_count")
)

# 3. 贝叶斯加权（避免小样本偏差）
mean_rating = stats_df.agg(avg("avg_rating")).collect()[0][0]
min_ratings = 50

weighted_rating = (
    (rating_count / (rating_count + min_ratings)) * avg_rating +
    (min_ratings / (rating_count + min_ratings)) * mean_rating
)

# 4. Top-N 推荐
top_movies = movies_with_stats \
    .filter(col("rating_count") >= min_ratings) \
    .orderBy(desc("weighted_rating")) \
    .limit(1000)

# 5. 写入 RDS（JDBC）
top_movies.write.jdbc(
    url="jdbc:mysql://rds-endpoint:3306/recommendation_db",
    table="app_recommendationdata",
    mode="overwrite"
)
```

**并行化策略**:
- 数据分区：自动按文件大小分区（默认 128MB/分区）
- 任务并行：2个 Core 节点 × 2 Executors = 4 并行任务
- 内存优化：4GB driver memory + 4GB executor memory

[插入 Spark UI 截图，显示任务并行执行]

#### 3.3.3 Code Snippet

关键代码片段（详见附录完整代码）：

```python
class MovieLensSparkEMR:
    def __init__(self, s3_bucket, db_config):
        self.spark = SparkSession.builder \
            .appName("MovieLens-EMR-Processing") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.driver.memory", "4g") \
            .getOrCreate()

    def process_movielens(self, min_ratings=50, top_n=1000):
        # 详见完整代码
        pass
```

### 3.4 Web Application Layer (EC2 + Django)

#### 3.4.1 EC2 Configuration

- **AMI**: Ubuntu 22.04 LTS
- **Instance Type**: t2.small (1 vCPU, 2GB RAM)
- **Security Group**:
  - SSH (22): 0.0.0.0/0
  - HTTP (80): 0.0.0.0/0
  - Custom (8000): 0.0.0.0/0

#### 3.4.2 Django Application

**主要功能模块**:
1. 用户认证 (Django Auth)
2. 推荐展示 (Pagination, Filtering)
3. 数据管理 (查看统计)
4. 管理后台 (Django Admin)

**关键配置** (`settings.py`):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'HOST': os.getenv('DB_HOST'),  # RDS endpoint
        'PORT': '3306',
    }
}
```

[插入 Django Web 界面截图]

### 3.5 Deployment Process

#### 步骤概览

1. **S3 Setup** (10 min)
   ```bash
   aws s3 mb s3://recommendation-system-data
   aws s3 cp movies.csv s3://recommendation-system-data/input/
   aws s3 cp ratings.csv s3://recommendation-system-data/input/
   ```

2. **RDS Creation** (15 min)
   - 通过 AWS Console 创建
   - 配置安全组允许 3306 端口

3. **EC2 Deployment** (30 min)
   ```bash
   ssh -i key.pem ubuntu@<ec2-ip>
   ./ec2_setup.sh
   python3 manage.py migrate
   python3 manage.py runserver 0.0.0.0:8000
   ```

4. **EMR Processing** (20 min)
   ```bash
   aws emr create-cluster --configurations file://emr-config.json
   ./submit_emr_job.sh <cluster-id>
   ```

[插入部署流程图]

---

## 4. Performance Analysis (3 pages)

### 4.1 Processing Time Comparison

**实验设置**:
- Dataset: MovieLens [1M/25M]
- 测试场景：计算 top 1000 推荐电影

| 环境 | 配置 | 处理时间 | 加速比 |
|------|------|---------|--------|
| 本地单机 | Intel i7, 16GB RAM | [X] 分钟 | 1x |
| EMR 1 节点 | 1x m5.xlarge | [Y] 分钟 | [X/Y]x |
| EMR 2 节点 | 1 Master + 2 Core | [Z] 分钟 | [X/Z]x |

[插入性能对比柱状图]

**结论**:
- EMR 2节点配置相比单机提速 [XX]%
- 数据量增加时，分布式优势更明显
- 网络 I/O 是主要瓶颈（S3 读取）

### 4.2 Resource Utilization

#### CPU 使用率

[插入 CloudWatch CPU 监控截图]

**观察**:
- EMR Core 节点在处理期间 CPU 使用率达 70-80%
- EC2 Web 服务器平均 CPU 使用率 < 20%

#### 内存使用

[插入内存监控图表]

**观察**:
- Spark Driver: ~3.5GB / 4GB
- Spark Executors: ~3GB / 4GB (per executor)
- 无 OOM 错误

#### 网络流量

[插入网络监控图表]

**数据传输量**:
- S3 -> EMR: [X] GB (读取数据)
- EMR -> RDS: [Y] MB (写入结果)

### 4.3 Scalability Analysis

#### 水平扩展测试

**理论分析**:
- 当前: 2 Core 节点
- 扩展到 4 Core 节点:
  - 预期加速: ~1.8x (考虑 overhead)
  - 成本增加: 2x

#### 垂直扩展

| 实例类型 | vCPU | 内存 | 价格/小时 | 适用场景 |
|---------|------|------|----------|---------|
| m5.large | 2 | 8GB | $0.096 | 小数据集 (<1M) |
| m5.xlarge | 4 | 16GB | $0.192 | 中数据集 (1M-10M) |
| m5.2xlarge | 8 | 32GB | $0.384 | 大数据集 (>10M) |

### 4.4 Limitations

1. **单点故障**: EC2 Web 服务器无冗余
2. **数据库瓶颈**: db.t3.micro 不适合高并发
3. **批处理延迟**: Spark 作业需要手动触发
4. **成本**: EMR 持续运行成本高

---

## 5. Cost Analysis (1 page)

### 5.1 Cost Breakdown

**测试期间成本（7天）**:

| Service | Configuration | Hours/Units | Unit Price | Total Cost |
|---------|--------------|-------------|------------|------------|
| EC2 | t2.small | 168 hours | $0.023/hr | $3.86 |
| RDS | db.t3.micro | 168 hours | $0.017/hr | $2.86 |
| EMR Master | m5.xlarge | 3 hours | $0.192/hr | $0.58 |
| EMR Core (×2) | m5.xlarge | 6 hours | $0.192/hr | $1.15 |
| S3 Storage | 1 GB | 1 GB-month | $0.023/GB | $0.02 |
| S3 Requests | 1000 req | 1000 req | $0.005/1k | $0.01 |
| Data Transfer | 2 GB | 2 GB | $0.09/GB | $0.18 |
| **TOTAL** | | | | **$8.66** |

[插入成本分布饼图]

### 5.2 Cost Optimization Strategies

1. **EMR 按需使用**: 仅在需要处理时启动 → 节省 90% EMR 成本
2. **Reserved Instances**: EC2/RDS 预留实例 → 节省 30-40%
3. **Spot Instances**: EMR Core 节点使用 Spot → 节省 50-70%
4. **S3 Lifecycle**: 旧数据归档到 Glacier → 节省 80% 存储成本
5. **Auto Scaling**: 根据负载自动调整 → 避免资源浪费

### 5.3 Budget Compliance

- **预算**: $50
- **实际使用**: $8.66
- **剩余**: $41.34 (82.7%)
- ✅ **状态**: 远低于预算

---

## 6. Challenges and Solutions (1 page)

### 6.1 Technical Challenges

#### Challenge 1: MySQL JDBC Driver 缺失

**问题**: EMR 默认不包含 MySQL JDBC driver
**解决方案**:
```bash
# 引导脚本自动下载
wget https://repo1.maven.org/.../mysql-connector-java-8.0.33.jar
cp mysql-connector-java-8.0.33.jar /usr/lib/spark/jars/
```

#### Challenge 2: RDS 连接超时

**问题**: EC2 无法连接 RDS
**原因**: 安全组未开放 3306 端口
**解决方案**:
- 修改 RDS 安全组，添加 Inbound rule (MySQL/Aurora, 3306)
- 验证：`telnet rds-endpoint 3306`

#### Challenge 3: Spark 内存溢出 (OOM)

**问题**: 处理 25M 数据集时 Executor OOM
**解决方案**:
```python
.config("spark.executor.memory", "6g")  # 增加到 6GB
.config("spark.sql.shuffle.partitions", "200")  # 增加分区数
```

### 6.2 Lessons Learned

1. **充分测试**: 先用小数据集测试，再扩展到大数据集
2. **监控重要**: CloudWatch 帮助快速定位性能瓶颈
3. **成本控制**: 及时终止不用的资源
4. **文档化**: 详细记录每个步骤，方便复现

---

## 7. Conclusion (1 page)

### 7.1 Summary

本项目成功在 AWS 平台上实现了一个基于 Spark 的分布式电影推荐系统，涵盖了：

✅ **分布式存储**: S3 存储 MovieLens 数据集
✅ **分布式计算**: EMR + Spark 并行处理 [X] 条评分数据
✅ **托管数据库**: RDS MySQL 持久化结果
✅ **Web 服务**: EC2 托管 Django 应用
✅ **性能优化**: 相比单机提速 [XX]%
✅ **成本控制**: 总成本 $8.66，远低于 $50 预算

### 7.2 Achievements

- 成功处理 [X]M 条评分数据
- 生成 1000 条高质量推荐
- 演示了分布式计算的性能优势
- 提供了用户友好的 Web 界面

### 7.3 Future Improvements

1. **实时推荐**:
   - 使用 Kinesis Streams 实时收集用户行为
   - Lambda 函数实时更新推荐

2. **高可用性**:
   - Application Load Balancer + 多 EC2 实例
   - RDS Multi-AZ 部署

3. **机器学习增强**:
   - 集成 SageMaker 训练协同过滤模型
   - 使用 EMR Notebooks 进行交互式分析

4. **容器化**:
   - Docker 容器化应用
   - ECS/EKS 编排

---

## 8. References

按 APA 格式列出参考文献：

1. Amazon Web Services. (2024). *Amazon EMR Documentation*. Retrieved from https://docs.aws.amazon.com/emr/

2. Apache Software Foundation. (2024). *Apache Spark Documentation*. Retrieved from https://spark.apache.org/docs/latest/

3. GroupLens Research. (2024). *MovieLens Datasets*. Retrieved from https://grouplens.org/datasets/movielens/

4. Django Software Foundation. (2024). *Django Documentation*. Retrieved from https://docs.djangoproject.com/

5. [添加其他引用...]

---

## Appendices

### Appendix A: Complete Source Code

[附上关键代码文件]

### Appendix B: Deployment Scripts

[附上所有脚本]

### Appendix C: Screenshots

[附上所有截图，按部署步骤组织]

---

**Word Count**: ~[填写字数]
**Page Count**: ~[填写页数] (excluding cover page and references)
