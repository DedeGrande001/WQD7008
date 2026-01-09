# EC2 部署命令指南

## 1️⃣ 更新系统并安装基础工具

```bash
# 更新系统包
sudo yum update -y

# 安装 Git
sudo yum install git -y

# 安装 Python 3.9+
sudo yum install python3 python3-pip -y

# 验证安装
python3 --version
git --version
```

## 2️⃣ 安装 MySQL 客户端库（用于连接 RDS）

```bash
# Amazon Linux 2023
sudo yum install python3-devel mysql-devel gcc -y

# 或者 Ubuntu/Debian
# sudo apt-get install python3-dev libmysqlclient-dev gcc -y
```

## 3️⃣ 克隆项目代码

```bash
# 进入工作目录
cd ~

# 克隆项目（替换为你的 Git 仓库地址）
git clone https://github.com/your-username/recommendation-system.git

# 进入项目目录
cd recommendation-system

# 查看项目结构
ls -la
```

## 4️⃣ 创建 Python 虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

## 5️⃣ 安装 Python 依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 验证安装
pip list
```

## 6️⃣ 配置环境变量

```bash
# 创建 .env 文件
cat > .env << 'EOF'
# Database Configuration
DB_NAME=recommendation_db
DB_USER=admin
DB_PASSWORD=your_rds_password
DB_HOST=recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com
DB_PORT=3306

# Django Secret Key
SECRET_KEY=django-insecure-movie-recommendation-dev-key-2024

# Debug Mode
DEBUG=False
EOF

# 查看配置（确保不显示密码）
cat .env | grep -v PASSWORD
```

## 7️⃣ 测试数据库连接

```bash
# 测试 MySQL 连接（需要先安装 mysql 命令行工具）
sudo yum install mysql -y

# 连接到 RDS
mysql -h recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com \
      -u admin \
      -p \
      recommendation_db

# 输入密码后，如果连接成功，输入 exit 退出
```

## 8️⃣ 运行数据库迁移

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 创建数据库表
python manage.py migrate

# 验证表已创建
python manage.py dbshell
# 在 MySQL shell 中：
# SHOW TABLES;
# exit;
```

## 9️⃣ 上传数据文件到 S3（可选，用于 EMR 处理）

```bash
# 如果数据文件已在本地，上传到 S3
aws s3 cp data/movies.csv s3://recommendation-system-data-dedegrande/input/
aws s3 cp data/ratings.csv s3://recommendation-system-data-dedegrande/input/

# 验证上传
aws s3 ls s3://recommendation-system-data-dedegrande/input/
```

## 🔟 启动 Django 开发服务器（测试）

```bash
# 方式1: 前台运行（用于测试）
python manage.py runserver 0.0.0.0:8000

# 方式2: 后台运行
nohup python manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &

# 查看日志
tail -f django.log

# 查看进程
ps aux | grep runserver

# 停止后台服务
pkill -f runserver
```

## 1️⃣1️⃣ 测试 API 端点

```bash
# 获取 EC2 公网 IP
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "EC2 Public IP: $EC2_IP"

# 测试健康检查
curl http://$EC2_IP:8000/health/

# 测试统计接口
curl http://$EC2_IP:8000/stats/

# 测试推荐接口
curl http://$EC2_IP:8000/recommendations/?limit=5
```

## 1️⃣2️⃣ 生产环境部署（使用 Gunicorn）

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动 Gunicorn
gunicorn recommendation_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --daemon \
    --access-logfile gunicorn-access.log \
    --error-logfile gunicorn-error.log

# 查看日志
tail -f gunicorn-access.log
tail -f gunicorn-error.log

# 停止 Gunicorn
pkill gunicorn
```

## 1️⃣3️⃣ 设置开机自启动（systemd 服务）

```bash
# 创建 systemd 服务文件
sudo cat > /etc/systemd/system/recommendation.service << 'EOF'
[Unit]
Description=Movie Recommendation System
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/recommendation-system
Environment="PATH=/home/ec2-user/recommendation-system/venv/bin"
ExecStart=/home/ec2-user/recommendation-system/venv/bin/gunicorn \
    recommendation_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start recommendation

# 查看服务状态
sudo systemctl status recommendation

# 设置开机自启
sudo systemctl enable recommendation

# 其他命令
# sudo systemctl stop recommendation    # 停止
# sudo systemctl restart recommendation # 重启
# sudo journalctl -u recommendation -f  # 查看日志
```

## 🔥 快速部署脚本（一键执行）

```bash
# 创建快速部署脚本
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 开始部署..."

# 1. 更新系统
echo "📦 更新系统包..."
sudo yum update -y

# 2. 安装工具
echo "🔧 安装必要工具..."
sudo yum install git python3 python3-pip python3-devel mysql-devel gcc mysql -y

# 3. 创建虚拟环境
echo "🐍 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
echo "📚 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 5. 配置环境变量（需要手动编辑 .env）
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，请手动创建！"
    exit 1
fi

# 6. 运行数据库迁移
echo "🗄️  运行数据库迁移..."
python manage.py migrate

# 7. 启动服务
echo "✅ 启动服务..."
gunicorn recommendation_system.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --daemon \
    --access-logfile gunicorn-access.log \
    --error-logfile gunicorn-error.log

echo "🎉 部署完成！"
echo "📊 访问: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/health/"
EOF

# 添加执行权限
chmod +x deploy.sh

# 运行部署
./deploy.sh
```

## 📋 常用运维命令

```bash
# 查看 Python 进程
ps aux | grep python

# 查看端口占用
sudo netstat -tlnp | grep 8000
# 或
sudo ss -tlnp | grep 8000

# 查看系统资源
top
htop  # 需要安装: sudo yum install htop -y

# 查看磁盘空间
df -h

# 查看内存使用
free -h

# 查看日志（实时）
tail -f django.log
tail -f gunicorn-error.log

# 查看安全组设置
aws ec2 describe-security-groups --group-ids sg-xxxxx

# 清理磁盘空间
sudo yum clean all
rm -rf ~/.cache/pip
```

## 🔒 安全配置检查清单

- [ ] EC2 安全组允许端口 8000 入站
- [ ] RDS 安全组允许 EC2 安全组访问 3306 端口
- [ ] .env 文件权限设置为 600
- [ ] 生产环境设置 DEBUG=False
- [ ] 更换默认 SECRET_KEY
- [ ] 配置 ALLOWED_HOSTS

```bash
# 设置 .env 文件权限
chmod 600 .env

# 检查 Django 配置
python manage.py check --deploy
```

## 🆘 故障排查

### 数据库连接失败
```bash
# 检查 RDS 端点
nslookup recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com

# 测试端口连通性
telnet recommendation-db.croqeqgd3egv.us-east-1.rds.amazonaws.com 3306

# 检查安全组规则
aws ec2 describe-security-groups --group-ids sg-xxxxx
```

### 服务无法访问
```bash
# 检查服务是否运行
ps aux | grep gunicorn

# 检查端口监听
sudo netstat -tlnp | grep 8000

# 检查防火墙
sudo firewall-cmd --list-all  # CentOS/RHEL
sudo ufw status               # Ubuntu
```

### 依赖安装失败
```bash
# 更新编译工具
sudo yum groupinstall "Development Tools" -y

# 手动安装 mysqlclient
pip install mysqlclient==2.2.0 --no-cache-dir
```

---

**部署完成后访问：**
- Health Check: `http://<EC2-IP>:8000/health/`
- Statistics: `http://<EC2-IP>:8000/stats/`
- Recommendations: `http://<EC2-IP>:8000/recommendations/`
