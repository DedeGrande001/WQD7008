# AWS Distributed Recommendation System

Distributed movie recommendation system deployed on AWS using EMR Spark, RDS MySQL, and EC2.

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────────────────────────┐
│  EC2 (Django API)               │
│  - Health check: /health/       │
│  - Statistics: /stats/          │
│  - Recommendations: /recommendations/ │
│  - Admin: /admin/               │
└────────┬────────────────────────┘
         │ MySQL
         ↓
┌─────────────────────────────────┐
│  RDS MySQL Database             │
│  - app_movie                    │
│  - app_recommendationdata       │
└────────┬────────────────────────┘
         ↑ JDBC Write
         │
┌─────────────────────────────────┐
│  EMR Spark Cluster              │
│  - Distributed Processing       │
│  - Bayesian Rating Algorithm    │
└────────┬────────────────────────┘
         ↑ Read CSV
         │
┌─────────────────────────────────┐
│  S3 Storage                     │
│  - input/movies.csv             │
│  - input/ratings.csv            │
│  - scripts/spark_emr.py         │
└─────────────────────────────────┘
```

## Quick Start

### AWS Deployment

See `aws_deployment/📖_从这里开始.md` for complete deployment guide.

**Quick steps:**
1. Upload data to S3
2. Create RDS MySQL database
3. Launch EC2 and clone this repo
4. Run `aws_deployment/ec2_setup.sh`
5. Configure `.env` file
6. Start Django: `python3 manage.py runserver 0.0.0.0:8000`
7. Create EMR cluster and submit Spark job

## API Endpoints

- `GET /` - Health check
- `GET /health/` - Health check
- `GET /stats/` - System statistics (JSON)
- `GET /recommendations/` - Get recommendations (JSON)
- `GET /admin/` - Django admin panel

## Technology Stack

- **Web Framework**: Django 4.2
- **Database**: MySQL (RDS)
- **Processing**: Apache Spark on EMR
- **Storage**: AWS S3
- **Compute**: AWS EC2

## Cost: ~$8-10/week (within $50 budget)
