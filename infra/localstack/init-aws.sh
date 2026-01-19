#!/bin/bash
set -e

echo "Creating SQS queues..."
awslocal sqs create-queue --queue-name sima-ingest-queue
awslocal sqs create-queue --queue-name sima-ingest-dlq

echo "Creating S3 buckets..."
awslocal s3 mb s3://sima-events-dev

echo "LocalStack initialization complete!"
