# S3 module for SIMA event payload storage

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Event Payloads Bucket
resource "aws_s3_bucket" "events" {
  bucket = "sima-${var.environment}-events-${var.aws_account_id}"

  tags = {
    Name        = "sima-${var.environment}-events"
    Environment = var.environment
    Service     = "sima"
    Purpose     = "event-payloads"
  }
}

# Versioning
resource "aws_s3_bucket_versioning" "events" {
  bucket = aws_s3_bucket.events.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "events" {
  bucket = aws_s3_bucket.events.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "events" {
  bucket = aws_s3_bucket.events.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules
resource "aws_s3_bucket_lifecycle_configuration" "events" {
  bucket = aws_s3_bucket.events.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = var.retention_days
    }
  }
}

# IAM policy for bucket access
data "aws_iam_policy_document" "events_access" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.events.arn,
      "${aws_s3_bucket.events.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "events_access" {
  name        = "sima-${var.environment}-s3-events-access"
  description = "Policy to access SIMA events S3 bucket"
  policy      = data.aws_iam_policy_document.events_access.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}
