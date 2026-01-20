# Secrets Manager module for SIMA credentials

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Database credentials secret
resource "aws_secretsmanager_secret" "database" {
  name                    = "sima/${var.environment}/database"
  description             = "Database credentials for SIMA"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "database-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username          = var.db_username
    password          = var.db_password
    host              = var.db_host
    port              = var.db_port
    database          = var.db_name
    connection_string = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${var.db_host}:${var.db_port}/${var.db_name}"
  })
}

# Telegram bot credentials
resource "aws_secretsmanager_secret" "telegram" {
  name                    = "sima/${var.environment}/telegram"
  description             = "Telegram bot credentials for SIMA"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "telegram-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "telegram" {
  secret_id = aws_secretsmanager_secret.telegram.id
  secret_string = jsonencode({
    bot_token     = var.telegram_bot_token
    chat_id       = var.telegram_chat_id
    conscious_channel_id    = var.telegram_conscious_channel_id
    subconscious_channel_id = var.telegram_subconscious_channel_id
    sleep_channel_id        = var.telegram_sleep_channel_id
  })
}

# LLM API keys
resource "aws_secretsmanager_secret" "llm_keys" {
  name                    = "sima/${var.environment}/llm-keys"
  description             = "LLM API keys for SIMA"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "llm-api-keys"
  }
}

resource "aws_secretsmanager_secret_version" "llm_keys" {
  secret_id = aws_secretsmanager_secret.llm_keys.id
  secret_string = jsonencode({
    openai_api_key  = var.openai_api_key
    google_api_key  = var.google_api_key
    xai_api_key     = var.xai_api_key
    anthropic_api_key = var.anthropic_api_key
  })
}

# Application secrets (JWT, lab password, etc.)
resource "aws_secretsmanager_secret" "app" {
  name                    = "sima/${var.environment}/app"
  description             = "Application secrets for SIMA"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "app-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    jwt_secret     = var.jwt_secret
    lab_password   = var.lab_password
    admin_username = var.admin_username
    admin_password = var.admin_password
  })
}

# IAM policy for reading secrets
data "aws_iam_policy_document" "read_secrets" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [
      aws_secretsmanager_secret.database.arn,
      aws_secretsmanager_secret.telegram.arn,
      aws_secretsmanager_secret.llm_keys.arn,
      aws_secretsmanager_secret.app.arn,
    ]
  }
}

resource "aws_iam_policy" "read_secrets" {
  name        = "sima-${var.environment}-read-secrets"
  description = "Policy to read SIMA secrets"
  policy      = data.aws_iam_policy_document.read_secrets.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}
