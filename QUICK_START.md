# 🚀 快速启动指南

## 最简部署流程（3 分钟）

### 1. 连接到 EC2
```bash
# 使用 EC2 Instance Connect（浏览器方式）
# 或使用 SSH
ssh -i your-key.pem ec2-user@54.164.120.161
```

### 2. 一键安装所有依赖
```bash
# 更新系统并安装所有必要工具
sudo yum update -y && \
sudo yum install -y git python3 python3-pip python3-devel mysql-devel gcc mysql
```

### 3. 克隆项目
```bash
# 进入主目录
cd ~

# 克隆项目（替换为你的仓库地址）
git clone https://github.com/your-username/recommendation-system.git
cd recommendation-system
```

### 4. 配置环境
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建 .env 配置文件
cat > .env << 'EOF'
DB_NAME=recommendation_db
DB_USER=admin
DB_PASSWORD=YOUR_PASSWORD_HERE
DB_HOST=recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com
DB_PORT=3306
SECRET_KEY=django-insecure-movie-recommendation-dev-key-2024
DEBUG=False
EOF

# ⚠️ 记得修改上面的 YOUR_PASSWORD_HERE 为你的真实 RDS 密码！
nano .env  # 或使用 vim .env 编辑
```

### 5. 初始化数据库
```bash
# 运行迁移，创建数据库表
python manage.py migrate

# 验证表已创建
echo "SHOW TABLES;" | python manage.py dbshell
```

### 6. 启动服务
```bash
# 简单启动（测试用）
python manage.py runserver 0.0.0.0:8000

# 或后台启动
nohup python manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &
```

### 7. 测试 API
```bash
# 在另一个终端窗口，或本地电脑浏览器访问
curl http://54.164.120.161:8000/health/
curl http://54.164.120.161:8000/stats/
curl http://54.164.120.161:8000/recommendations/?limit=5
```

---

## 🔧 常用命令速查

### 服务管理
```bash
# 查看运行中的服务
ps aux | grep python

# 停止服务
pkill -f runserver

# 重启服务
pkill -f runserver && \
nohup python manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &

# 查看日志
tail -f django.log
```

### 数据库操作
```bash
# 进入 Django shell
python manage.py dbshell

# 查看数据
echo "SELECT COUNT(*) FROM movies;" | python manage.py dbshell
echo "SELECT COUNT(*) FROM recommendation_data;" | python manage.py dbshell
```

### 代码更新
```bash
# 拉取最新代码
git pull origin main

# 重启服务应用更新
pkill -f runserver
source venv/bin/activate
python manage.py migrate
nohup python manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &
```

---

## ⚠️ 重要提醒

### 安全组配置
确保 EC2 安全组允许以下入站规则：
- **类型**: Custom TCP
- **端口**: 8000
- **源**: 0.0.0.0/0（或你的 IP）

### RDS 连接
确保 RDS 安全组允许：
- **类型**: MySQL/Aurora
- **端口**: 3306
- **源**: EC2 安全组 ID

### 验证清单
- [ ] EC2 可以访问 RDS（测试: `mysql -h <RDS-ENDPOINT> -u admin -p`）
- [ ] 端口 8000 已开放（测试: `curl http://localhost:8000/health/`）
- [ ] .env 文件配置正确
- [ ] 数据库迁移成功（`python manage.py migrate`）
- [ ] 可以从外网访问 API

---

## 📊 数据处理流程

### 方式 1: 本地 Spark 处理（测试用）
```bash
# 确保 CSV 文件在 data/ 目录
ls -lh data/movies.csv data/ratings.csv

# 安装 PySpark
pip install pyspark

# 运行本地测试
python test_spark_local.py
```

### 方式 2: EMR 集群处理（生产用）
```bash
# 上传数据到 S3
aws s3 cp data/movies.csv s3://recommendation-system-data-dedegrande/input/
aws s3 cp data/ratings.csv s3://recommendation-system-data-dedegrande/input/

# 提交 Spark 作业到 EMR（需要创建 EMR 集群）
# 参考 EMR_SETUP.md
```

---

## 🆘 问题排查

### 问题 1: 无法连接数据库
```bash
# 测试 RDS 连通性
mysql -h recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com \
      -u admin -p recommendation_db

# 如果连接失败，检查：
# 1. RDS 安全组是否允许 EC2 安全组
# 2. .env 中的数据库配置是否正确
# 3. RDS 实例是否正在运行
```

### 问题 2: API 无法访问
```bash
# 检查服务是否运行
ps aux | grep python

# 检查端口监听
sudo netstat -tlnp | grep 8000

# 检查日志
tail -50 django.log
```

### 问题 3: 依赖安装失败
```bash
# 更新 pip
pip install --upgrade pip

# 手动安装问题依赖
pip install mysqlclient==2.2.0 --no-cache-dir

# 如果还失败，安装编译工具
sudo yum groupinstall "Development Tools" -y
```

---

## 📱 API 端点说明

| 端点 | 方法 | 描述 | 示例 |
|------|------|------|------|
| `/health/` | GET | 健康检查 | `curl http://IP:8000/health/` |
| `/stats/` | GET | 系统统计 | `curl http://IP:8000/stats/` |
| `/recommendations/` | GET | 获取推荐 | `curl http://IP:8000/recommendations/?limit=10` |

### 推荐 API 参数
- `limit`: 返回数量（默认 20）
- `offset`: 偏移量（分页用）
- `genre`: 类型过滤（如 "Action", "Drama"）

示例：
```bash
# 获取前 10 条推荐
curl http://IP:8000/recommendations/?limit=10

# 获取动作片推荐
curl http://IP:8000/recommendations/?genre=Action&limit=5

# 分页查询
curl http://IP:8000/recommendations/?limit=10&offset=20
```

---

**需要详细说明？** 查看完整文档：
- `EC2_SETUP.md` - 详细部署步骤
- `DEPLOY.md` - 项目架构说明
- `README.md` - 项目概述
