# SSM Parameter Store module for SIMA credentials
#
# Each value the ECS tasks consume is one SecureString parameter under
# /secrets/sima/<environment>/, encrypted with the account's aws/ssm key.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

data "aws_region" "current" {}

locals {
  prefix = "/secrets/sima/${var.environment}"

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# Database connection string
resource "aws_ssm_parameter" "database_url" {
  name        = "${local.prefix}/database-url"
  description = "SIMA database connection string"
  type        = "SecureString"
  value       = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${var.db_host}:${var.db_port}/${var.db_name}"
  tags        = merge(local.tags, { Purpose = "database-credentials" })
}

# Telegram bot credentials
resource "aws_ssm_parameter" "telegram_bot_token" {
  name        = "${local.prefix}/telegram-bot-token"
  description = "SIMA Telegram bot token"
  type        = "SecureString"
  value       = var.telegram_bot_token
  tags        = merge(local.tags, { Purpose = "telegram-credentials" })
}

# LLM API key
resource "aws_ssm_parameter" "openai_api_key" {
  name        = "${local.prefix}/openai-api-key"
  description = "SIMA OpenAI API key"
  type        = "SecureString"
  value       = var.openai_api_key
  tags        = merge(local.tags, { Purpose = "llm-api-keys" })
}

# Application secrets (JWT, admin credentials)
resource "aws_ssm_parameter" "jwt_secret" {
  name        = "${local.prefix}/jwt-secret"
  description = "SIMA JWT signing secret"
  type        = "SecureString"
  value       = var.jwt_secret
  tags        = merge(local.tags, { Purpose = "app-secrets" })
}

resource "aws_ssm_parameter" "admin_username" {
  name        = "${local.prefix}/admin-username"
  description = "SIMA admin username"
  type        = "SecureString"
  value       = var.admin_username
  tags        = merge(local.tags, { Purpose = "app-secrets" })
}

resource "aws_ssm_parameter" "admin_password" {
  name        = "${local.prefix}/admin-password"
  description = "SIMA admin password"
  type        = "SecureString"
  value       = var.admin_password
  tags        = merge(local.tags, { Purpose = "app-secrets" })
}

locals {
  parameters = {
    database_url       = aws_ssm_parameter.database_url
    telegram_bot_token = aws_ssm_parameter.telegram_bot_token
    openai_api_key     = aws_ssm_parameter.openai_api_key
    jwt_secret         = aws_ssm_parameter.jwt_secret
    admin_username     = aws_ssm_parameter.admin_username
    admin_password     = aws_ssm_parameter.admin_password
  }
}

# IAM policy for reading the parameters (ECS resolves task secrets with
# ssm:GetParameters; SecureString values decrypt through the aws/ssm key).
data "aws_iam_policy_document" "read_secrets" {
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [for p in local.parameters : p.arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${data.aws_region.current.name}.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "read_secrets" {
  name        = "sima-${var.environment}-read-secrets"
  description = "Policy to read SIMA secrets"
  policy      = data.aws_iam_policy_document.read_secrets.json

  tags = local.tags
}
