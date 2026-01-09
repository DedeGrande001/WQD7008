#!/bin/bash

# EC2 Setup Script for Django Recommendation System
# Run this script on your EC2 instance after initial connection

set -e  # Exit on error

echo "=========================================="
echo "EC2 Setup for Django Recommendation System"
echo "=========================================="

# Update system
echo -e "\n[1/7] Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python and development tools
echo -e "\n[2/7] Installing Python and development tools..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libmysqlclient-dev \
    pkg-config \
    git \
    nginx \
    mysql-client

# Install AWS CLI
echo -e "\n[3/7] Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt install -y unzip
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Verify installations
echo -e "\n[4/7] Verifying installations..."
python3 --version
pip3 --version
aws --version

# Create project directory
echo -e "\n[5/7] Setting up project directory..."
cd /home/ubuntu
PROJECT_DIR="/home/ubuntu/recommendation_system"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Creating project directory..."
    mkdir -p $PROJECT_DIR
fi

# Install Python packages (without PySpark, will run on EMR)
echo -e "\n[6/7] Installing Python dependencies..."
cat > /tmp/requirements_ec2.txt << 'EOF'
Django==4.2.0
mysqlclient==2.2.0
pandas==2.0.0
numpy==1.24.0
python-dotenv==1.0.0
gunicorn==21.2.0
boto3==1.28.0
EOF

pip3 install -r /tmp/requirements_ec2.txt

# Configure firewall (UFW)
echo -e "\n[7/7] Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
# Don't enable UFW yet, as it might lock you out
# sudo ufw --force enable

echo -e "\n=========================================="
echo "✅ EC2 Setup Completed Successfully!"
echo "=========================================="
echo -e "\nNext Steps:"
echo "1. Upload your project files to $PROJECT_DIR"
echo "   scp -i key.pem -r project_files ubuntu@<EC2-IP>:/home/ubuntu/"
echo ""
echo "2. Configure environment variables"
echo "   cd $PROJECT_DIR"
echo "   cp aws_deployment/.env.aws .env"
echo "   nano .env  # Edit with your RDS credentials"
echo ""
echo "3. Run database migrations"
echo "   python3 manage.py migrate"
echo "   python3 manage.py createsuperuser"
echo ""
echo "4. Start Django server"
echo "   python3 manage.py runserver 0.0.0.0:8000"
echo ""
echo "   Or run in background:"
echo "   nohup python3 manage.py runserver 0.0.0.0:8000 > django.log 2>&1 &"
echo ""
echo "Access your application at: http://<EC2-Public-IP>:8000"
echo "=========================================="
