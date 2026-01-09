# Data Directory

This directory is used to store uploaded CSV datasets.

## CSV Format Example

Your dataset should be in CSV format. Here's an example structure:

```csv
item_id,item_name,category,score,description
1,Product A,Electronics,4.5,Great electronic device
2,Product B,Books,4.2,Bestselling book
3,Product C,Clothing,3.8,Comfortable wear
```

## Required Columns (customize in Spark job)

The Spark processing script can be customized to match your data structure.

## Upload via Web Interface

1. Go to Data Management page
2. Click "Upload New Dataset"
3. Select your CSV file
4. Click "Upload Dataset"
5. Process with Spark

## Sample Data

You can create a sample CSV file for testing. Place it here and reference it in the Spark job configuration.
