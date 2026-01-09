# AWS Deployment Guide - 最小可行方案 (MVP)

## 架构概览

```
用户浏览器
    ↓
EC2 (Django Web 服务器) ←→ RDS MySQL (数据库)
    ↓ 触发处理
S3 存储桶 (MovieLens 数据)
    ↓
EMR 集群 (Spark 分布式处理 - 按需启动)
    ↓ 写回结果
RDS MySQL
    ↓
Web 界面展示推荐结果
```

## 预计成本（总计 $5-10）

- **S3**: ~$0.10 (存储 1GB MovieLens 数据)
- **RDS MySQL (db.t3.micro)**: ~$0.017/小时 × 24小时 = $0.41/天
- **EC2 (t2.small)**: ~$0.023/小时 × 24小时 = $0.55/天
- **EMR (按需)**: ~$0.27/小时 × 2小时 = $0.54 (仅演示时启动)
- **数据传输**: ~$0.50

**总计**: 约 $5-10（远低于 $50 预算）

---

## 部署步骤

### 准备工作

1. 登录 AWS Learner Lab
2. 确保有 $50 credit
3. 下载 MovieLens 1M 数据集（简化版，约 24MB）
   - 网址: https://grouplens.org/datasets/movielens/1m/
   - 或使用现有的 25M 数据集（需要更多处理时间）

---

## Step 1: 创建 S3 存储桶（15分钟）

### 1.1 在 AWS 控制台创建 S3 bucket

```bash
Bucket名称: recommendation-system-data-[your-name]
区域: us-east-1 (或任意区域)
公共访问: 全部阻止（默认）
```

### 1.2 上传数据文件

创建文件夹结构：
```
recommendation-system-data/
├── input/
│   ├── movies.csv
│   └── ratings.csv
└── scripts/
    └── spark_emr.py (稍后上传)
```

### 1.3 使用 AWS CLI 上传（可选）

```bash
# 配置 AWS CLI
aws configure

# 上传数据
aws s3 cp data/movies.csv s3://recommendation-system-data-[your-name]/input/
aws s3 cp data/ratings.csv s3://recommendation-system-data-[your-name]/input/
```

**截图保存**: S3 控制台显示文件列表

---

## Step 2: 创建 RDS MySQL 数据库（20分钟）

### 2.1 在 RDS 控制台创建数据库

**配置参数**:
```
引擎: MySQL 8.0
模板: 免费套餐
数据库实例标识符: recommendation-db
主用户名: admin
主密码: [设置一个强密码，例如: RecommendDB2026!]

实例配置:
- 实例类型: db.t3.micro (免费套餐)
- 存储: 20GB (免费套餐)

连接:
- 公开访问: 是 (方便开发，生产环境应设为否)
- VPC 安全组: 创建新的 (rds-sg)
- 可用区: 无偏好

其他:
- 初始数据库名: recommendation_db
- 自动备份: 禁用 (节省成本)
- 删除保护: 禁用 (方便清理)
```

### 2.2 配置安全组

创建后，修改安全组 `rds-sg`:
```
入站规则:
- 类型: MySQL/Aurora
- 端口: 3306
- 来源: 0.0.0.0/0 (开发环境，生产环境应限制为特定 IP)
```

### 2.3 获取连接端点

等待数据库创建完成（约5-10分钟），记录：
```
端点: recommendation-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com
端口: 3306
用户名: admin
密码: [你设置的密码]
数据库名: recommendation_db
```

**截图保存**: RDS 实例详情页面

---

## Step 3: 创建 EC2 实例（30分钟）

### 3.1 启动 EC2 实例

**配置参数**:
```
名称: recommendation-web-server
AMI: Ubuntu Server 22.04 LTS (HVM)
实例类型: t2.small (1 vCPU, 2GB RAM)

密钥对: 创建新的密钥对 (recommendation-key.pem) - 下载并保存
网络设置:
- VPC: 默认
- 自动分配公有 IP: 启用
- 安全组: 创建新的 (web-server-sg)
  入站规则:
  - SSH (22): 0.0.0.0/0
  - HTTP (80): 0.0.0.0/0
  - 自定义 TCP (8000): 0.0.0.0/0

存储: 8GB (默认)
```

### 3.2 连接到 EC2

**Windows 用户**:
```bash
# 使用 PuTTY 或 Git Bash
ssh -i recommendation-key.pem ubuntu@<EC2-Public-IP>
```

**Mac/Linux 用户**:
```bash
chmod 400 recommendation-key.pem
ssh -i recommendation-key.pem ubuntu@<EC2-Public-IP>
```

### 3.3 安装依赖

SSH 连接后，执行 `ec2_setup.sh` 脚本（见下面文件）

**截图保存**: EC2 实例列表，显示运行状态

---

## Step 4: 部署 Django 应用到 EC2（30分钟）

### 4.1 上传项目文件

**方法1: 使用 Git**
```bash
# 在 EC2 上
cd /home/ubuntu
git clone <your-repo-url> recommendation_system
```

**方法2: 使用 SCP**
```bash
# 在本地电脑
scp -i recommendation-key.pem -r d:\myproject\recommendation_system ubuntu@<EC2-IP>:/home/ubuntu/
```

### 4.2 配置环境变量

```bash
cd /home/ubuntu/recommendation_system
cp aws_deployment/.env.aws .env

# 编辑 .env 文件，填入 RDS 连接信息
nano .env
```

填入内容：
```
DB_HOST=recommendation-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com
DB_NAME=recommendation_db
DB_USER=admin
DB_PASSWORD=RecommendDB2026!
DB_PORT=3306

SECRET_KEY=your-random-secret-key-here
DEBUG=True

# AWS 配置
AWS_REGION=us-east-1
S3_BUCKET=recommendation-system-data-[your-name]
```

### 4.3 安装 Python 依赖

```bash
cd /home/ubuntu/recommendation_system
pip3 install -r aws_deployment/requirements_ec2.txt
```

### 4.4 运行数据库迁移

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
# 创建管理员账户: admin / admin@example.com / YourPassword123
```

### 4.5 启动 Django 服务

```bash
# 测试运行
python3 manage.py runserver 0.0.0.0:8000

# 后台运行（推荐）
nohup python3 manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &
```

### 4.6 验证

浏览器访问: `http://<EC2-Public-IP>:8000`

**截图保存**: 登录页面、仪表盘页面

---

## Step 5: 创建 EMR 集群（按需启动，20分钟）

⚠️ **重要**: EMR 集群按小时计费，只在需要处理数据或演示时启动！

### 5.1 创建 EMR 集群

**配置参数**:
```
集群名称: recommendation-spark-cluster
版本: emr-6.15.0 (Spark 3.4.1, Hadoop 3.3.3)

应用程序:
- ✓ Spark
- ✓ Hadoop
- ✓ Hive (可选)

硬件配置:
- 实例类型: m5.xlarge
- 实例数量:
  - Master: 1
  - Core: 2 (展示分布式能力)
  - Task: 0

网络:
- VPC: 默认
- 子网: 任意公有子网

安全和访问:
- EC2 密钥对: recommendation-key (之前创建的)
- IAM 角色: EMR_DefaultRole, EMR_EC2_DefaultRole (自动创建)

引导操作:
- 添加自定义引导脚本: s3://recommendation-system-data-[your-name]/scripts/bootstrap.sh
```

### 5.2 配置安全组

EMR 自动创建安全组，需要修改 Master 节点安全组：
```
入站规则添加:
- SSH (22): 0.0.0.0/0 (方便调试)
```

### 5.3 等待集群启动

启动时间: 约 10-15 分钟

**截图保存**: EMR 集群列表，显示 "Waiting" 或 "Running" 状态

---

## Step 6: 提交 Spark 作业到 EMR（15分钟）

### 6.1 确保 Spark 脚本已上传到 S3

```bash
# 在本地或 EC2 上
aws s3 cp aws_deployment/spark_emr.py s3://recommendation-system-data-[your-name]/scripts/
```

### 6.2 通过 AWS CLI 提交作业

```bash
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="MovieLens Processing",ActionOnFailure=CONTINUE,Args=[--deploy-mode,cluster,--master,yarn,--conf,spark.yarn.submit.waitAppCompletion=true,s3://recommendation-system-data-[your-name]/scripts/spark_emr.py,--s3-bucket,recommendation-system-data-[your-name],--db-host,recommendation-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com,--db-name,recommendation_db,--db-user,admin,--db-password,RecommendDB2026!]
```

### 6.3 监控作业执行

**方法1: AWS 控制台**
- 进入 EMR 集群详情
- 查看 "Steps" 选项卡
- 查看作业状态和日志

**方法2: Spark UI**
- 启用 EMR SSH 隧道
- 访问 `http://localhost:8157` 查看 Spark UI

**截图保存**:
- Step 执行成功的截图
- Spark UI 显示任务并行执行的截图
- CloudWatch 监控图表

---

## Step 7: 验证和测试（15分钟）

### 7.1 检查数据库

连接到 RDS（从 EC2 或本地）:
```bash
mysql -h recommendation-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com -u admin -p recommendation_db

# 查询数据
SELECT COUNT(*) FROM app_movie;
SELECT COUNT(*) FROM app_recommendationdata;
SELECT title, recommendation_score FROM app_recommendationdata
JOIN app_movie ON app_recommendationdata.movie_id = app_movie.movie_id
ORDER BY recommendation_score DESC LIMIT 10;
```

**截图保存**: 数据库查询结果

### 7.2 访问 Web 界面

访问: `http://<EC2-Public-IP>:8000/recommendations/`

**截图保存**: 推荐结果页面

---

## Step 8: 性能监控和成本分析（收集数据）

### 8.1 CloudWatch 监控

查看以下指标：
- EC2: CPU 使用率、网络流量
- RDS: CPU 使用率、数据库连接数
- EMR: 集群利用率、任务执行时间

**截图保存**: CloudWatch 控制台的监控图表

### 8.2 成本预估

在 AWS Billing Dashboard 查看:
- 当前支出
- 预计月度费用
- 各服务费用明细

**截图保存**: Billing 仪表盘

---

## Step 9: 清理资源（节省成本）

### 演示后，按以下顺序清理：

1. **终止 EMR 集群** (最重要！)
   ```bash
   aws emr terminate-clusters --cluster-ids j-XXXXXXXXXXXXX
   ```

2. **停止 EC2 实例** (可选，保留数据)
   - 控制台 → EC2 → 实例 → 停止

3. **删除 RDS 实例** (最终演示后)
   - 控制台 → RDS → 删除
   - 取消勾选 "创建最终快照"

4. **清空 S3 存储桶** (可选)
   ```bash
   aws s3 rm s3://recommendation-system-data-[your-name] --recursive
   ```

---

## 常见问题排查

### 1. EC2 无法连接到 RDS
- 检查 RDS 安全组是否允许 3306 端口
- 检查 RDS 公开访问是否启用
- 测试连接: `telnet <RDS-endpoint> 3306`

### 2. EMR 作业失败
- 查看 EMR Step 日志
- 检查 S3 路径是否正确
- 验证 IAM 角色权限

### 3. Django 无法启动
- 检查 .env 文件配置
- 查看 django.log: `tail -f django.log`
- 检查端口 8000 是否被占用: `netstat -tulpn | grep 8000`

### 4. Spark 内存不足
- 增加 EMR 实例大小（m5.xlarge → m5.2xlarge）
- 减少数据集大小（使用 MovieLens 1M）

---

## 技术报告要点

### 需要包含的内容：

1. **架构图** (使用 draw.io 或 AWS Architecture Icons)
2. **部署步骤详细说明**
3. **关键代码片段** (Spark 处理逻辑)
4. **性能测试结果**:
   - 单机处理时间 vs EMR 处理时间
   - CPU/内存使用对比
5. **成本分析表格**
6. **截图证据** (至少 15 张)
7. **遇到的挑战和解决方案**
8. **可扩展性分析**
9. **参考文献** (APA 格式)

---

## 下一步

请按照以下顺序执行文件：

1. ✅ 阅读本文件 (README.md)
2. → 执行 `ec2_setup.sh` (在 EC2 上)
3. → 配置 `.env.aws` (环境变量)
4. → 运行 `spark_emr.py` (在 EMR 上)
5. → 使用 `submit_emr_job.sh` (提交作业脚本)

所有脚本和配置文件都在 `aws_deployment/` 文件夹中。

---

**预计总时间**: 3-4 小时（首次部署）
**难度**: 中等
**推荐测试次数**: 2-3 次（确保演示顺利）

祝部署顺利！🚀
