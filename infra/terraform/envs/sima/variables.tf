# Variables for SIMA environment

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

# SSL Certificate
variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = "arn:aws:acm:us-east-1:322989427387:certificate/61276ff0-4c76-4fdf-9c27-b74548dba9c9"
}

# Route53
variable "route53_zone_id" {
  description = "Route53 hosted zone ID for talsai.com"
  type        = string
  default     = "Z00776272HR3DF9HW018X"
}

# Telegram credentials
variable "telegram_bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "telegram_chat_id" {
  description = "Telegram chat ID"
  type        = string
  default     = ""
}

variable "telegram_conscious_channel_id" {
  description = "Telegram conscious stream channel ID"
  type        = string
  default     = ""
}

variable "telegram_subconscious_channel_id" {
  description = "Telegram subconscious stream channel ID"
  type        = string
  default     = ""
}

variable "telegram_sleep_channel_id" {
  description = "Telegram sleep stream channel ID"
  type        = string
  default     = ""
}

# LLM API Keys
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_api_key" {
  description = "Google AI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "xai_api_key" {
  description = "xAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

# Application secrets
variable "lab_password" {
  description = "Lab access password"
  type        = string
  sensitive   = true
  default     = ""
}
