# Outputs for ECR module

output "repository_urls" {
  description = "Map of service name to repository URL"
  value       = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}

output "repository_arns" {
  description = "Map of service name to repository ARN"
  value       = { for k, v in aws_ecr_repository.services : k => v.arn }
}

output "web_repository_url" {
  description = "Web service repository URL"
  value       = aws_ecr_repository.services["web"].repository_url
}

output "api_repository_url" {
  description = "API service repository URL"
  value       = aws_ecr_repository.services["api"].repository_url
}

output "ingest_repository_url" {
  description = "Ingest API service repository URL"
  value       = aws_ecr_repository.services["ingest-api"].repository_url
}

output "orchestrator_repository_url" {
  description = "Orchestrator service repository URL"
  value       = aws_ecr_repository.services["orchestrator"].repository_url
}

output "sleep_repository_url" {
  description = "Sleep service repository URL"
  value       = aws_ecr_repository.services["sleep"].repository_url
}

output "push_policy_arn" {
  description = "ARN of IAM policy for pushing images"
  value       = aws_iam_policy.push_images.arn
}

output "pull_policy_arn" {
  description = "ARN of IAM policy for pulling images"
  value       = aws_iam_policy.pull_images.arn
}
