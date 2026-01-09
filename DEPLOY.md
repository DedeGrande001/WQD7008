# EC2 部署快速指南

## 1. 克隆项目

```bash
cd /home/ubuntu
git clone https://github.com/你的用户名/recommendation_system.git
cd recommendation_system
```

## 2. 安装依赖

```bash
cd aws_deployment
chmod +x ec2_setup.sh
sudo ./ec2_setup.sh
```

## 3. 配置环境变量

```bash
cd /home/ubuntu/recommendation_system
cp .env.example .env
nano .env
```

填写：
```
DB_HOST=你的RDS_Endpoint
DB_NAME=recommendation_db
DB_USER=admin
DB_PASSWORD=RecommendDB2026!
DB_PORT=3306
S3_BUCKET=recommendation-system-data-dedegrande
AWS_REGION=us-east-1
```

## 4. 初始化数据库

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

## 5. 启动服务

```bash
nohup python3 manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &
```

## 6. 测试 API

```bash
curl http://localhost:8000/health/
```

浏览器访问：`http://你的EC2公网IP:8000/`
