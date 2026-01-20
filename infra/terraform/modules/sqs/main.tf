# SQS module for SIMA message queues

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Dead Letter Queue
resource "aws_sqs_queue" "ingest_dlq" {
  name                      = "sima-${var.environment}-ingest-dlq"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "sima-${var.environment}-ingest-dlq"
    Environment = var.environment
    Service     = "sima"
    Purpose     = "dead-letter-queue"
  }
}

# Main Ingest Queue
resource "aws_sqs_queue" "ingest" {
  name                       = "sima-${var.environment}-ingest"
  visibility_timeout_seconds = var.visibility_timeout
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = var.receive_wait_time
  delay_seconds              = 0

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingest_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = {
    Name        = "sima-${var.environment}-ingest"
    Environment = var.environment
    Service     = "sima"
    Purpose     = "ingest-queue"
  }
}

# IAM policy for sending messages
data "aws_iam_policy_document" "send_messages" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes"
    ]
    resources = [
      aws_sqs_queue.ingest.arn
    ]
  }
}

resource "aws_iam_policy" "send_messages" {
  name        = "sima-${var.environment}-sqs-send"
  description = "Policy to send messages to SIMA ingest queue"
  policy      = data.aws_iam_policy_document.send_messages.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# IAM policy for receiving messages
data "aws_iam_policy_document" "receive_messages" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility"
    ]
    resources = [
      aws_sqs_queue.ingest.arn
    ]
  }
}

resource "aws_iam_policy" "receive_messages" {
  name        = "sima-${var.environment}-sqs-receive"
  description = "Policy to receive messages from SIMA ingest queue"
  policy      = data.aws_iam_policy_document.receive_messages.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# IAM policy for DLQ access (for monitoring/reprocessing)
data "aws_iam_policy_document" "dlq_access" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes",
      "sqs:SendMessage"
    ]
    resources = [
      aws_sqs_queue.ingest_dlq.arn
    ]
  }
}

resource "aws_iam_policy" "dlq_access" {
  name        = "sima-${var.environment}-sqs-dlq"
  description = "Policy to access SIMA DLQ"
  policy      = data.aws_iam_policy_document.dlq_access.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}
