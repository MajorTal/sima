# RDS PostgreSQL module for SIMA

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name        = "sima-${var.environment}"
  description = "Subnet group for SIMA RDS"
  subnet_ids  = var.subnet_ids

  tags = {
    Name        = "sima-${var.environment}-db-subnet-group"
    Environment = var.environment
    Service     = "sima"
  }
}

# Parameter Group for PostgreSQL 16
resource "aws_db_parameter_group" "main" {
  family      = "postgres16"
  name        = "sima-${var.environment}-pg16"
  description = "Parameter group for SIMA PostgreSQL 16"

  # Enable pg_stat_statements for monitoring (static param, needs reboot)
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "sima-${var.environment}"

  # Engine
  engine               = "postgres"
  engine_version       = "16.6"
  instance_class       = var.instance_class
  parameter_group_name = aws_db_parameter_group.main.name

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = var.security_group_ids
  publicly_accessible    = false
  multi_az               = var.multi_az

  # Backup
  backup_retention_period = var.backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"
  copy_tags_to_snapshot   = true
  skip_final_snapshot     = var.environment == "dev"
  final_snapshot_identifier = var.environment == "prod" ? "sima-${var.environment}-final-snapshot" : null

  # Monitoring
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null
  monitoring_interval                   = var.monitoring_interval
  monitoring_role_arn                   = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null
  enabled_cloudwatch_logs_exports       = ["postgresql"]

  # Other
  auto_minor_version_upgrade = true
  deletion_protection        = var.environment == "prod"

  tags = {
    Name        = "sima-${var.environment}-postgres"
    Environment = var.environment
    Service     = "sima"
  }
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  name  = "sima-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.monitoring_interval > 0 ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
