# Outputs for SIMA environment

output "url" {
  description = "SIMA URL"
  value       = "https://sima.talsai.com"
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.alb_dns_name
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs"
  value       = module.ecr.repository_urls
}

output "sqs_queue_url" {
  description = "SQS ingest queue URL"
  value       = module.sqs.ingest_queue_url
}

output "s3_bucket_name" {
  description = "S3 events bucket name"
  value       = module.s3.events_bucket_id
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = module.ecs.log_group_name
}
