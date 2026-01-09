# 🚀 快速开始指南 - AWS 部署

这个指南会带你快速部署系统到 AWS。预计总时间：**2-3 小时**

---

## 📋 前置检查清单

在开始之前，确保你有：

- [ ] AWS Learner Lab 账户（有 $50 credit）
- [ ] 本地已安装 AWS CLI
- [ ] SSH 客户端（Git Bash, PuTTY, 或原生终端）
- [ ] MovieLens 数据集（1M 或 25M）
- [ ] 基本的 Linux 命令知识

---

## 🎯 部署流程概览

```
1. 准备数据 (15分钟)
   └─> 下载 MovieLens 数据集

2. 创建 S3 存储桶 (10分钟)
   └─> 上传 movies.csv 和 ratings.csv

3. 创建 RDS 数据库 (20分钟)
   └─> 配置 MySQL 实例

4. 启动 EC2 实例 (30分钟)
   └─> 部署 Django Web 应用

5. 创建 EMR 集群 (20分钟，按需)
   └─> 配置 Spark 处理环境

6. 运行 Spark 作业 (15分钟)
   └─> 生成推荐数据

7. 验证和测试 (15分钟)
   └─> 检查 Web 界面
```

---

## Step 1️⃣: 准备数据（本地操作）

### 下载 MovieLens 数据集

**选项 A：MovieLens 1M（推荐用于快速测试）**
- 大小：约 24MB
- 下载地址：https://files.grouplens.org/datasets/movielens/ml-1m.zip

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://files.grouplens.org/datasets/movielens/ml-1m.zip" -OutFile "ml-1m.zip"
Expand-Archive -Path "ml-1m.zip" -DestinationPath "."

# Mac/Linux
wget https://files.grouplens.org/datasets/movielens/ml-1m.zip
unzip ml-1m.zip
```

**选项 B：使用现有的 MovieLens 25M**
- 位置：`d:\myproject\recommendation_system\data\`

### 准备 CSV 文件

确保你有：
- `movies.csv` - 电影信息
- `ratings.csv` - 用户评分

---

## Step 2️⃣: 创建 S3 存储桶

### 2.1 登录 AWS 控制台

1. 进入 AWS Learner Lab
2. 点击 "Start Lab"（等待 AWS 标志变绿）
3. 点击 "AWS" 进入控制台

### 2.2 创建 S3 Bucket

```bash
# 使用 AWS CLI（推荐）
aws s3 mb s3://recommendation-system-data-[你的名字]

# 或在 AWS 控制台手动创建
# Services -> S3 -> Create bucket
```

### 2.3 上传数据文件

```bash
# 创建文件夹结构
aws s3api put-object --bucket recommendation-system-data-[你的名字] --key input/
aws s3api put-object --bucket recommendation-system-data-[你的名字] --key scripts/

# 上传数据（替换为你的实际路径）
aws s3 cp movies.csv s3://recommendation-system-data-[你的名字]/input/
aws s3 cp ratings.csv s3://recommendation-system-data-[你的名字]/input/

# 上传引导脚本
cd d:\myproject\recommendation_system\aws_deployment
aws s3 cp bootstrap.sh s3://recommendation-system-data-[你的名字]/scripts/
aws s3 cp spark_emr.py s3://recommendation-system-data-[你的名字]/scripts/
```

**✅ 验证**：在 S3 控制台查看文件是否上传成功

**📸 截图保存**：S3 bucket 内容列表

---

## Step 3️⃣: 创建 RDS MySQL 数据库

### 3.1 启动创建向导

1. Services -> RDS -> Create database

### 3.2 配置参数（逐步填写）

**选择引擎**：
```
引擎类型: MySQL
版本: MySQL 8.0.35（或最新）
```

**模板**：
```
选择: Free tier（免费套餐）
```

**设置**：
```
数据库实例标识符: recommendation-db
主用户名: admin
主密码: RecommendDB2026!（或你自己设置的强密码）
确认密码: RecommendDB2026!
```

**实例配置**：
```
实例类型: db.t3.micro（已自动选择）
存储: 20 GB（默认）
```

**连接**：
```
✅ 公开访问: 是（Yes）
VPC 安全组: 创建新的
新 VPC 安全组名称: rds-sg
```

**其他设置**：
```
初始数据库名: recommendation_db
```

### 3.3 创建数据库

点击 **"Create database"**，等待 5-10 分钟

### 3.4 配置安全组

1. 等待数据库状态变为 "Available"
2. 点击数据库实例 -> Connectivity & security
3. 点击 VPC 安全组链接
4. Inbound rules -> Edit inbound rules
5. 添加规则：
   ```
   Type: MySQL/Aurora
   Port: 3306
   Source: 0.0.0.0/0（或你的 IP）
   Description: Allow MySQL access
   ```
6. Save rules

### 3.5 记录连接信息

在数据库详情页面，记录：
```
Endpoint: recommendation-db.xxxxx.us-east-1.rds.amazonaws.com
Port: 3306
Username: admin
Password: RecommendDB2026!
Database: recommendation_db
```

**📸 截图保存**：RDS 实例详情页面

---

## Step 4️⃣: 创建 EC2 实例并部署 Django

### 4.1 启动 EC2 实例

1. Services -> EC2 -> Launch instance

**配置**：
```
名称: recommendation-web-server
AMI: Ubuntu Server 22.04 LTS
实例类型: t2.small
```

**密钥对**：
```
创建新密钥对: recommendation-key
类型: RSA
格式: .pem（Mac/Linux）或 .ppk（Windows/PuTTY）
```

⚠️ **重要**：下载密钥对并保存到安全位置！

**网络设置**：
```
✅ 允许来自互联网的 SSH 流量
✅ 允许来自互联网的 HTTP 流量
添加安全组规则:
  - Type: Custom TCP
  - Port: 8000
  - Source: 0.0.0.0/0
```

### 4.2 连接到 EC2

获取公有 IP 地址（例如：3.85.123.45）

**Windows（Git Bash）**：
```bash
chmod 400 recommendation-key.pem
ssh -i recommendation-key.pem ubuntu@3.85.123.45
```

**Mac/Linux**：
```bash
chmod 400 recommendation-key.pem
ssh -i recommendation-key.pem ubuntu@3.85.123.45
```

### 4.3 运行设置脚本

```bash
# 下载设置脚本
wget https://raw.githubusercontent.com/[your-repo]/aws_deployment/ec2_setup.sh

# 或从本地上传
# 退出 SSH，在本地运行：
scp -i recommendation-key.pem d:\myproject\recommendation_system\aws_deployment\ec2_setup.sh ubuntu@3.85.123.45:/home/ubuntu/

# 回到 EC2，执行脚本
chmod +x ec2_setup.sh
./ec2_setup.sh
```

### 4.4 上传项目文件

**在本地电脑执行**：
```bash
cd d:\myproject
scp -i recommendation-key.pem -r recommendation_system ubuntu@3.85.123.45:/home/ubuntu/
```

### 4.5 配置环境变量

**回到 EC2 SSH 会话**：
```bash
cd /home/ubuntu/recommendation_system
cp aws_deployment/.env.aws .env
nano .env
```

**编辑 .env 文件**，替换为你的实际值：
```
DB_HOST=recommendation-db.xxxxx.us-east-1.rds.amazonaws.com
DB_NAME=recommendation_db
DB_USER=admin
DB_PASSWORD=RecommendDB2026!
DB_PORT=3306

S3_BUCKET=recommendation-system-data-[你的名字]
AWS_REGION=us-east-1
```

按 `Ctrl+O` 保存，`Ctrl+X` 退出

### 4.6 初始化数据库

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
# 输入用户名: admin
# 输入邮箱: admin@example.com
# 输入密码: Admin123!（两次）
```

### 4.7 启动 Django 服务

```bash
# 前台运行（测试用）
python3 manage.py runserver 0.0.0.0:8000

# 或后台运行
nohup python3 manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &
```

### 4.8 验证

浏览器访问：`http://3.85.123.45:8000`

你应该看到登录页面！

**📸 截图保存**：
- EC2 实例列表
- Django 登录页面
- Dashboard 页面

---

## Step 5️⃣: 创建 EMR 集群（按需启动）

⚠️ **重要提示**：EMR 按小时计费！只在需要处理数据时启动。

### 5.1 创建集群

1. Services -> EMR -> Create cluster

**配置**：
```
集群名称: recommendation-spark-cluster
版本: emr-6.15.0

应用程序:
- ✅ Spark
- ✅ Hadoop

实例类型: m5.xlarge
实例数:
- Master: 1
- Core: 1（最小配置，可选 2）

EC2 密钥对: recommendation-key
```

**引导操作**（可选，推荐）：
```
添加引导操作:
名称: Install MySQL Driver
脚本位置: s3://recommendation-system-data-[你的名字]/scripts/bootstrap.sh
```

### 5.2 启动集群

点击 **"Create cluster"**，等待 10-15 分钟

**📸 截图保存**：EMR 集群显示 "Waiting" 状态

---

## Step 6️⃣: 运行 Spark 作业

### 6.1 准备提交脚本

**在本地编辑** `aws_deployment/submit_emr_job.sh`：

修改配置变量：
```bash
CLUSTER_ID="j-XXXXXXXXXXXXX"  # 替换为你的集群 ID
S3_BUCKET="recommendation-system-data-[你的名字]"
DB_HOST="recommendation-db.xxxxx.us-east-1.rds.amazonaws.com"
DB_PASSWORD="RecommendDB2026!"
```

### 6.2 提交作业

```bash
cd d:\myproject\recommendation_system\aws_deployment
chmod +x submit_emr_job.sh
./submit_emr_job.sh j-XXXXXXXXXXXXX
```

### 6.3 监控执行

脚本会自动监控进度，你也可以在 EMR 控制台查看：
- Cluster -> Steps 标签
- 查看日志输出

处理时间：
- MovieLens 1M: ~3-5 分钟
- MovieLens 25M: ~10-15 分钟

**📸 截图保存**：
- EMR Step 显示 "Running"
- EMR Step 显示 "Completed"
- Spark UI（可选）

---

## Step 7️⃣: 验证结果

### 7.1 检查数据库

```bash
# 在 EC2 或本地
mysql -h recommendation-db.xxxxx.us-east-1.rds.amazonaws.com \
      -u admin -p recommendation_db

# 输入密码后，执行查询
SELECT COUNT(*) FROM app_movie;
SELECT COUNT(*) FROM app_recommendationdata;

SELECT m.title, r.recommendation_score
FROM app_recommendationdata r
JOIN app_movie m ON r.movie_id_ref = m.movie_id
ORDER BY r.recommendation_score DESC
LIMIT 10;
```

### 7.2 访问 Web 界面

访问：`http://3.85.123.45:8000/recommendations/`

你应该看到推荐的电影列表！

**📸 截图保存**：推荐结果页面

---

## 🎉 完成！

恭喜你成功部署了分布式推荐系统！

### 下一步：

1. **收集材料**：
   - 所有截图（至少 15 张）
   - CloudWatch 监控数据
   - 成本分析

2. **编写报告**：
   - 使用 `REPORT_TEMPLATE.md` 作为模板

3. **准备演示**：
   - 制作 PPT
   - 练习演示流程

4. **清理资源**（演示后）：
   ```bash
   # 终止 EMR 集群（最重要！）
   aws emr terminate-clusters --cluster-ids j-XXXXXXXXXXXXX

   # 停止 EC2
   aws ec2 stop-instances --instance-ids i-xxxxx

   # 删除 RDS（可选）
   # 在控制台手动删除
   ```

---

## 🆘 遇到问题？

参考 `README.md` 的 "常见问题排查" 部分

或查看详细日志：
```bash
# Django 日志
tail -f /home/ubuntu/recommendation_system/django.log

# EMR 日志
# 在 EMR 控制台 -> Steps -> View logs
```

---

**预计总成本**：$5-10
**部署时间**：2-3 小时
**难度**：⭐⭐⭐☆☆

祝你成功！🚀
