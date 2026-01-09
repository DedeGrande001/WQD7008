#!/bin/bash

# EMR Bootstrap Script
# Installs MySQL JDBC driver and Python packages

set -e

echo "=========================================="
echo "EMR Bootstrap - Installing Dependencies"
echo "=========================================="

# Install Python packages
echo "Installing Python packages..."
sudo pip3 install --upgrade pip
sudo pip3 install \
    pandas \
    numpy \
    mysql-connector-python \
    PyMySQL

# Download MySQL JDBC driver
echo "Downloading MySQL JDBC driver..."
cd /usr/lib/spark/jars/
sudo wget https://repo1.maven.org/maven2/mysql/mysql-connector-java/8.0.33/mysql-connector-java-8.0.33.jar

echo "✅ Bootstrap completed successfully!"
