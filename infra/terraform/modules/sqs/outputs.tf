# Outputs for SQS module

output "ingest_queue_url" {
  description = "URL of the ingest queue"
  value       = aws_sqs_queue.ingest.url
}

output "ingest_queue_arn" {
  description = "ARN of the ingest queue"
  value       = aws_sqs_queue.ingest.arn
}

output "ingest_queue_name" {
  description = "Name of the ingest queue"
  value       = aws_sqs_queue.ingest.name
}

output "dlq_url" {
  description = "URL of the dead letter queue"
  value       = aws_sqs_queue.ingest_dlq.url
}

output "dlq_arn" {
  description = "ARN of the dead letter queue"
  value       = aws_sqs_queue.ingest_dlq.arn
}

output "send_policy_arn" {
  description = "ARN of IAM policy for sending messages"
  value       = aws_iam_policy.send_messages.arn
}

output "receive_policy_arn" {
  description = "ARN of IAM policy for receiving messages"
  value       = aws_iam_policy.receive_messages.arn
}

output "dlq_policy_arn" {
  description = "ARN of IAM policy for DLQ access"
  value       = aws_iam_policy.dlq_access.arn
}
