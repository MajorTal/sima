# Outputs for S3 module

output "events_bucket_id" {
  description = "Events bucket ID"
  value       = aws_s3_bucket.events.id
}

output "events_bucket_arn" {
  description = "Events bucket ARN"
  value       = aws_s3_bucket.events.arn
}

output "events_bucket_domain_name" {
  description = "Events bucket domain name"
  value       = aws_s3_bucket.events.bucket_domain_name
}

output "events_access_policy_arn" {
  description = "ARN of IAM policy for bucket access"
  value       = aws_iam_policy.events_access.arn
}
