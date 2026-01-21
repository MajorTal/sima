# SIMA Infrastructure - sima.talsai.com
# Single environment deployment without redundancy

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "private"

  default_tags {
    tags = {
      Project   = "sima"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = false
}

# Random secret for JWT
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

locals {
  environment = "sima"
  domain_name = "sima.talsai.com"
}

# =============================================================================
# VPC
# =============================================================================
module "vpc" {
  source = "../../modules/vpc"

  environment        = local.environment
  vpc_cidr           = "10.2.0.0/16"
  az_count           = 2
  enable_nat_gateway = true
}

# =============================================================================
# Secrets Manager
# =============================================================================
module "secrets" {
  source = "../../modules/secrets"

  environment = local.environment

  # Database
  db_username = "sima"
  db_password = random_password.db_password.result
  db_host     = module.rds.address
  db_port     = 5432
  db_name     = "sima"

  # Telegram
  telegram_bot_token               = var.telegram_bot_token
  telegram_chat_id                 = var.telegram_chat_id
  telegram_conscious_channel_id    = var.telegram_conscious_channel_id
  telegram_subconscious_channel_id = var.telegram_subconscious_channel_id
  telegram_sleep_channel_id        = var.telegram_sleep_channel_id

  # LLM API Keys
  openai_api_key    = var.openai_api_key
  google_api_key    = var.google_api_key
  xai_api_key       = var.xai_api_key
  anthropic_api_key = var.anthropic_api_key

  # Application
  jwt_secret     = random_password.jwt_secret.result
  lab_password   = var.lab_password
  admin_username = var.admin_username
  admin_password = var.admin_password

  depends_on = [module.rds]
}

# =============================================================================
# RDS PostgreSQL (no Multi-AZ)
# =============================================================================
module "rds" {
  source = "../../modules/rds"

  environment        = local.environment
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.rds_security_group_id]

  instance_class        = "db.t4g.micro"
  allocated_storage     = 20
  max_allocated_storage = 100

  db_name     = "sima"
  db_username = "sima"
  db_password = random_password.db_password.result

  multi_az              = false
  backup_retention_days = 7

  enable_performance_insights = false
  monitoring_interval         = 0
}

# =============================================================================
# S3 Bucket
# =============================================================================
module "s3" {
  source = "../../modules/s3"

  environment       = local.environment
  aws_account_id    = data.aws_caller_identity.current.account_id
  enable_versioning = true
  retention_days    = 180
}

# =============================================================================
# SQS Queue
# =============================================================================
module "sqs" {
  source = "../../modules/sqs"

  environment        = local.environment
  visibility_timeout = 300
  max_receive_count  = 3
}

# =============================================================================
# ECR Repositories
# =============================================================================
module "ecr" {
  source = "../../modules/ecr"

  environment           = local.environment
  scan_on_push          = true
  image_retention_count = 10
  untagged_image_days   = 7
}

# =============================================================================
# ALB
# =============================================================================
module "alb" {
  source = "../../modules/alb"

  environment       = local.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  certificate_arn   = var.certificate_arn
}

# =============================================================================
# ECS Cluster and Services
# =============================================================================
module "ecs" {
  source = "../../modules/ecs"

  environment = local.environment
  aws_region  = var.aws_region

  # Network
  private_subnet_ids    = module.vpc.private_subnet_ids
  ecs_security_group_id = module.vpc.ecs_tasks_security_group_id

  # ECR
  ecr_repository_urls = module.ecr.repository_urls
  ecr_pull_policy_arn = module.ecr.pull_policy_arn
  image_tag           = var.image_tag

  # Secrets
  secrets_policy_arn  = module.secrets.read_secrets_policy_arn
  database_secret_arn = module.secrets.database_secret_arn
  telegram_secret_arn = module.secrets.telegram_secret_arn
  llm_secret_arn      = module.secrets.llm_keys_secret_arn
  app_secret_arn      = module.secrets.app_secret_arn

  # S3 and SQS
  s3_policy_arn          = module.s3.events_access_policy_arn
  s3_bucket_name         = module.s3.events_bucket_id
  sqs_send_policy_arn    = module.sqs.send_policy_arn
  sqs_receive_policy_arn = module.sqs.receive_policy_arn
  sqs_queue_url          = module.sqs.ingest_queue_url

  # Load Balancer
  web_target_group_arn    = module.alb.web_target_group_arn
  api_target_group_arn    = module.alb.api_target_group_arn
  ingest_target_group_arn = module.alb.ingest_target_group_arn

  # URLs
  api_url = "https://${local.domain_name}"
  ws_url  = "wss://${local.domain_name}"

  # Single instance settings
  enable_container_insights = false
  use_fargate_spot          = true
  log_retention_days        = 30

  web_cpu           = 256
  web_memory        = 512
  web_desired_count = 1

  api_cpu           = 256
  api_memory        = 512
  api_desired_count = 1

  ingest_cpu           = 256
  ingest_memory        = 512
  ingest_desired_count = 1

  brain_cpu           = 512
  brain_memory        = 1024
  brain_desired_count = 1

  # Brain tick settings
  minute_tick_enabled     = true
  autonomous_tick_enabled = true
  brain_timezone   = "Asia/Jerusalem"

  sleep_cpu             = 512
  sleep_memory          = 1024
  enable_sleep_schedule = true
  sleep_schedule        = "cron(0 4 * * ? *)"
}

# =============================================================================
# EventBridge (Time-based triggers)
# =============================================================================
module "eventbridge" {
  source = "../../modules/eventbridge"

  environment   = local.environment
  sqs_queue_arn = module.sqs.ingest_queue_arn
  sqs_queue_url = module.sqs.ingest_queue_url

  minute_tick_enabled     = true
  autonomous_tick_enabled = true
  autonomous_tick_rate    = "rate(10 minutes)"
}

# =============================================================================
# Route53 A Record
# =============================================================================
resource "aws_route53_record" "main" {
  zone_id = var.route53_zone_id
  name    = local.domain_name
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}
