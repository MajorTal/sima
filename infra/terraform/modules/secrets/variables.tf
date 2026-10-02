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

# LLM API key
variable "openai_api_key" {
  description = "OpenAI API key"
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
