# Variables for ECS module

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# Network
variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

# ECR
variable "ecr_repository_urls" {
  description = "Map of service name to ECR repository URL"
  type        = map(string)
}

variable "ecr_pull_policy_arn" {
  description = "ARN of IAM policy for pulling ECR images"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

# Secrets
variable "secrets_policy_arn" {
  description = "ARN of IAM policy for reading secrets"
  type        = string
}

variable "database_secret_arn" {
  description = "ARN of database credentials secret"
  type        = string
}

variable "telegram_secret_arn" {
  description = "ARN of Telegram credentials secret"
  type        = string
}

variable "llm_secret_arn" {
  description = "ARN of LLM API keys secret"
  type        = string
}

variable "app_secret_arn" {
  description = "ARN of app secrets"
  type        = string
}

# S3 and SQS
variable "s3_policy_arn" {
  description = "ARN of IAM policy for S3 access"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of S3 bucket for events"
  type        = string
}

variable "sqs_send_policy_arn" {
  description = "ARN of IAM policy for sending SQS messages"
  type        = string
}

variable "sqs_receive_policy_arn" {
  description = "ARN of IAM policy for receiving SQS messages"
  type        = string
}

variable "sqs_queue_url" {
  description = "URL of the SQS ingest queue"
  type        = string
}

# Load Balancer Target Groups
variable "web_target_group_arn" {
  description = "ARN of web service target group"
  type        = string
}

variable "api_target_group_arn" {
  description = "ARN of API service target group"
  type        = string
}

variable "ingest_target_group_arn" {
  description = "ARN of ingest API service target group"
  type        = string
}

# URLs for frontend configuration
variable "api_url" {
  description = "Public URL for API"
  type        = string
}

variable "ws_url" {
  description = "WebSocket URL for API"
  type        = string
}

# Cluster settings
variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
  default     = true
}

variable "use_fargate_spot" {
  description = "Use Fargate Spot for cost savings"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Web service settings
variable "web_cpu" {
  description = "CPU units for web service"
  type        = number
  default     = 256
}

variable "web_memory" {
  description = "Memory (MB) for web service"
  type        = number
  default     = 512
}

variable "web_desired_count" {
  description = "Desired task count for web service"
  type        = number
  default     = 1
}

# API service settings
variable "api_cpu" {
  description = "CPU units for API service"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "Memory (MB) for API service"
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Desired task count for API service"
  type        = number
  default     = 1
}

# Ingest service settings
variable "ingest_cpu" {
  description = "CPU units for ingest service"
  type        = number
  default     = 256
}

variable "ingest_memory" {
  description = "Memory (MB) for ingest service"
  type        = number
  default     = 512
}

variable "ingest_desired_count" {
  description = "Desired task count for ingest service"
  type        = number
  default     = 1
}

# Orchestrator service settings
variable "orchestrator_cpu" {
  description = "CPU units for orchestrator service"
  type        = number
  default     = 512
}

variable "orchestrator_memory" {
  description = "Memory (MB) for orchestrator service"
  type        = number
  default     = 1024
}

variable "orchestrator_desired_count" {
  description = "Desired task count for orchestrator service"
  type        = number
  default     = 1
}

# Sleep service settings
variable "sleep_cpu" {
  description = "CPU units for sleep service"
  type        = number
  default     = 512
}

variable "sleep_memory" {
  description = "Memory (MB) for sleep service"
  type        = number
  default     = 1024
}

variable "enable_sleep_schedule" {
  description = "Enable scheduled sleep consolidation"
  type        = bool
  default     = true
}

variable "sleep_schedule" {
  description = "Cron expression for sleep schedule"
  type        = string
  default     = "cron(0 4 * * ? *)"  # 4 AM UTC daily
}

# Orchestrator tick settings
variable "minute_tick_enabled" {
  description = "Enable minute tick events in orchestrator"
  type        = bool
  default     = true
}

variable "autonomous_tick_enabled" {
  description = "Enable autonomous tick events in orchestrator"
  type        = bool
  default     = true
}

variable "orchestrator_timezone" {
  description = "Timezone for orchestrator"
  type        = string
  default     = "UTC"
}
