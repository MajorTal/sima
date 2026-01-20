# Outputs for Secrets module

output "database_secret_arn" {
  description = "ARN of database credentials secret"
  value       = aws_secretsmanager_secret.database.arn
}

output "telegram_secret_arn" {
  description = "ARN of Telegram credentials secret"
  value       = aws_secretsmanager_secret.telegram.arn
}

output "llm_keys_secret_arn" {
  description = "ARN of LLM API keys secret"
  value       = aws_secretsmanager_secret.llm_keys.arn
}

output "app_secret_arn" {
  description = "ARN of application secrets"
  value       = aws_secretsmanager_secret.app.arn
}

output "read_secrets_policy_arn" {
  description = "ARN of IAM policy for reading secrets"
  value       = aws_iam_policy.read_secrets.arn
}

output "secret_arns" {
  description = "List of all secret ARNs"
  value = [
    aws_secretsmanager_secret.database.arn,
    aws_secretsmanager_secret.telegram.arn,
    aws_secretsmanager_secret.llm_keys.arn,
    aws_secretsmanager_secret.app.arn,
  ]
}
