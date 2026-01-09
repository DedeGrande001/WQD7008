#!/bin/bash

# Submit Spark Job to EMR Cluster
# Usage: ./submit_emr_job.sh <cluster-id>

set -e

# Configuration - REPLACE THESE VALUES
CLUSTER_ID="${1:-j-XXXXXXXXXXXXX}"  # Pass as argument or set default
S3_BUCKET="recommendation-system-data-yourname"
DB_HOST="recommendation-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com"
DB_NAME="recommendation_db"
DB_USER="admin"
DB_PASSWORD="YourPassword123!"
DB_PORT="3306"
MIN_RATINGS="50"
TOP_N="1000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "Submitting Spark Job to EMR"
echo -e "==========================================${NC}"

# Validate inputs
if [ "$CLUSTER_ID" == "j-XXXXXXXXXXXXX" ]; then
    echo -e "${RED}ERROR: Please provide a valid EMR cluster ID${NC}"
    echo "Usage: $0 <cluster-id>"
    echo "Example: $0 j-2AXXXXXXXXXX"
    exit 1
fi

# Check if cluster exists and is running
echo -e "\n${YELLOW}Checking cluster status...${NC}"
CLUSTER_STATE=$(aws emr describe-cluster --cluster-id $CLUSTER_ID --query 'Cluster.Status.State' --output text)

if [ "$CLUSTER_STATE" != "WAITING" ] && [ "$CLUSTER_STATE" != "RUNNING" ]; then
    echo -e "${RED}ERROR: Cluster $CLUSTER_ID is not in WAITING or RUNNING state${NC}"
    echo "Current state: $CLUSTER_STATE"
    exit 1
fi

echo -e "${GREEN}✅ Cluster is $CLUSTER_STATE${NC}"

# Upload Spark script to S3
echo -e "\n${YELLOW}Uploading Spark script to S3...${NC}"
SCRIPT_PATH="s3://$S3_BUCKET/scripts/spark_emr.py"

aws s3 cp spark_emr.py $SCRIPT_PATH
echo -e "${GREEN}✅ Script uploaded to $SCRIPT_PATH${NC}"

# Submit Spark job
echo -e "\n${YELLOW}Submitting Spark job to EMR...${NC}"

STEP_ID=$(aws emr add-steps \
    --cluster-id $CLUSTER_ID \
    --steps Type=Spark,Name="MovieLens-Processing",ActionOnFailure=CONTINUE,Args=[--deploy-mode,cluster,--master,yarn,--conf,spark.yarn.submit.waitAppCompletion=true,--conf,spark.jars=/usr/lib/spark/jars/mysql-connector-java-8.0.33.jar,$SCRIPT_PATH,--s3-bucket,$S3_BUCKET,--db-host,$DB_HOST,--db-name,$DB_NAME,--db-user,$DB_USER,--db-password,$DB_PASSWORD,--db-port,$DB_PORT,--min-ratings,$MIN_RATINGS,--top-n,$TOP_N] \
    --query 'StepIds[0]' \
    --output text)

echo -e "${GREEN}✅ Step submitted successfully!${NC}"
echo -e "Step ID: ${YELLOW}$STEP_ID${NC}"

# Monitor step status
echo -e "\n${YELLOW}Monitoring step progress...${NC}"
echo "You can also view progress in the EMR console"
echo "Press Ctrl+C to stop monitoring (job will continue running)"
echo ""

while true; do
    STEP_STATE=$(aws emr describe-step --cluster-id $CLUSTER_ID --step-id $STEP_ID --query 'Step.Status.State' --output text)

    case $STEP_STATE in
        "PENDING")
            echo -e "${YELLOW}⏳ Status: PENDING - Waiting for resources...${NC}"
            ;;
        "RUNNING")
            echo -e "${YELLOW}▶️  Status: RUNNING - Processing data...${NC}"
            ;;
        "COMPLETED")
            echo -e "${GREEN}✅ Status: COMPLETED - Job finished successfully!${NC}"
            break
            ;;
        "FAILED")
            echo -e "${RED}❌ Status: FAILED - Job failed!${NC}"
            echo "Check logs in EMR console or S3"
            exit 1
            ;;
        "CANCELLED")
            echo -e "${RED}⚠️  Status: CANCELLED${NC}"
            exit 1
            ;;
    esac

    sleep 10
done

echo -e "\n${GREEN}=========================================="
echo "🎉 Spark Job Completed Successfully!"
echo -e "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Check your Django web interface to view recommendations"
echo "2. Verify data in RDS database"
echo "3. Collect screenshots for your report:"
echo "   - EMR console showing completed step"
echo "   - Spark UI (if enabled)"
echo "   - CloudWatch metrics"
echo ""
echo "Don't forget to terminate the EMR cluster to save costs!"
echo "Command: aws emr terminate-clusters --cluster-ids $CLUSTER_ID"
echo ""
