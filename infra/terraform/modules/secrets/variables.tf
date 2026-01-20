# Variables for Secrets module

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

# Database
variable "db_username" {
  description = "Database username"
  type        = string
  default     = "sima"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_host" {
  description = "Database host"
  type        = string
  default     = ""
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "sima"
}

# Telegram
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

# Application
variable "jwt_secret" {
  description = "JWT signing secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "lab_password" {
  description = "Lab access password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_username" {
  description = "Admin username for system reset"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_password" {
  description = "Admin password for system reset"
  type        = string
  sensitive   = true
  default     = ""
}
