# Outputs for Secrets module

output "parameter_arns" {
  description = "ARNs of the SecureString parameters, keyed by secret"
  value       = { for k, p in local.parameters : k => p.arn }
}

output "parameter_names" {
  description = "Names of the SecureString parameters, keyed by secret"
  value       = { for k, p in local.parameters : k => p.name }
}

output "read_secrets_policy_arn" {
  description = "ARN of IAM policy for reading secrets"
  value       = aws_iam_policy.read_secrets.arn
}
