@echo off
REM Windows Batch Script to Upload Files to S3
REM Usage: Double-click this file or run from command prompt

echo ================================================
echo AWS S3 Upload Script for MovieLens Data
echo ================================================
echo.

REM Configuration - CHANGE THESE VALUES
set S3_BUCKET=recommendation-system-data-dedegrande
set DATA_DIR=..\data

echo Checking AWS CLI installation...
aws --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: AWS CLI not found!
    echo Please install AWS CLI from: https://aws.amazon.com/cli/
    pause
    exit /b 1
)
echo OK - AWS CLI found
echo.

echo Checking AWS credentials...
aws sts get-caller-identity >nul 2>&1
if errorlevel 1 (
    echo ERROR: AWS credentials not configured!
    echo Please run: aws configure
    pause
    exit /b 1
)
echo OK - AWS credentials configured
echo.

REM Create S3 bucket if not exists
echo Creating S3 bucket: %S3_BUCKET%
aws s3 mb s3://%S3_BUCKET% 2>nul
if errorlevel 1 (
    echo Bucket already exists or creation failed - continuing...
) else (
    echo OK - Bucket created
)
echo.

REM Create folder structure
echo Creating folder structure in S3...
aws s3api put-object --bucket %S3_BUCKET% --key input/ >nul 2>&1
aws s3api put-object --bucket %S3_BUCKET% --key scripts/ >nul 2>&1
echo OK - Folders created
echo.

REM Upload data files
echo Uploading MovieLens data files...
echo This may take several minutes depending on file size...
echo.

if exist "%DATA_DIR%\movies.csv" (
    echo [1/4] Uploading movies.csv...
    aws s3 cp "%DATA_DIR%\movies.csv" s3://%S3_BUCKET%/input/
    if errorlevel 1 (
        echo ERROR: Failed to upload movies.csv
    ) else (
        echo OK - movies.csv uploaded
    )
) else (
    echo WARNING: movies.csv not found in %DATA_DIR%
)
echo.

if exist "%DATA_DIR%\ratings.csv" (
    echo [2/4] Uploading ratings.csv...
    aws s3 cp "%DATA_DIR%\ratings.csv" s3://%S3_BUCKET%/input/
    if errorlevel 1 (
        echo ERROR: Failed to upload ratings.csv
    ) else (
        echo OK - ratings.csv uploaded
    )
) else (
    echo WARNING: ratings.csv not found in %DATA_DIR%
)
echo.

REM Upload scripts
echo [3/4] Uploading Spark script...
aws s3 cp spark_emr.py s3://%S3_BUCKET%/scripts/
if errorlevel 1 (
    echo ERROR: Failed to upload spark_emr.py
) else (
    echo OK - spark_emr.py uploaded
)
echo.

echo [4/4] Uploading bootstrap script...
aws s3 cp bootstrap.sh s3://%S3_BUCKET%/scripts/
if errorlevel 1 (
    echo ERROR: Failed to upload bootstrap.sh
) else (
    echo OK - bootstrap.sh uploaded
)
echo.

REM Verify uploads
echo ================================================
echo Verifying uploads in S3...
echo ================================================
aws s3 ls s3://%S3_BUCKET%/input/
aws s3 ls s3://%S3_BUCKET%/scripts/
echo.

echo ================================================
echo Upload completed!
echo ================================================
echo.
echo Next steps:
echo 1. Create RDS database instance
echo 2. Create EC2 instance
echo 3. Create EMR cluster
echo 4. Run Spark job
echo.
echo See QUICKSTART.md for detailed instructions.
echo.

pause
