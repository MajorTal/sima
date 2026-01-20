# ECS Fargate module for SIMA services

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "sima-${var.environment}"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = {
    Name        = "sima-${var.environment}-cluster"
    Environment = var.environment
    Service     = "sima"
  }
}

# ECS Cluster Capacity Providers
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = var.use_fargate_spot ? "FARGATE_SPOT" : "FARGATE"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/sima-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "sima-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_execution_secrets" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = var.secrets_policy_arn
}

resource "aws_iam_role_policy_attachment" "ecs_execution_ecr" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = var.ecr_pull_policy_arn
}

# Task Role (for runtime permissions)
resource "aws_iam_role" "ecs_task" {
  name = "sima-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# Attach S3, SQS, and Secrets policies to task role
resource "aws_iam_role_policy_attachment" "ecs_task_s3" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = var.s3_policy_arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_sqs_send" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = var.sqs_send_policy_arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_sqs_receive" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = var.sqs_receive_policy_arn
}

resource "aws_iam_role_policy_attachment" "ecs_task_secrets" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = var.secrets_policy_arn
}

# =============================================================================
# Web Service (Next.js frontend)
# =============================================================================
resource "aws_ecs_task_definition" "web" {
  family                   = "sima-${var.environment}-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "web"
      image = "${var.ecr_repository_urls["web"]}:${var.image_tag}"
      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "NEXT_PUBLIC_API_URL", value = var.api_url },
        { name = "NEXT_PUBLIC_WS_URL", value = var.ws_url }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "web"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "web"
  }
}

resource "aws_ecs_service" "web" {
  name            = "sima-${var.environment}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.web_desired_count
  launch_type     = var.use_fargate_spot ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 100
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.web_target_group_arn
    container_name   = "web"
    container_port   = 3000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Environment = var.environment
    Service     = "web"
  }
}

# =============================================================================
# API Service (FastAPI backend)
# =============================================================================
resource "aws_ecs_task_definition" "api" {
  family                   = "sima-${var.environment}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${var.ecr_repository_urls["api"]}:${var.image_tag}"
      portMappings = [
        {
          containerPort = 8001
          hostPort      = 8001
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "HOST", value = "0.0.0.0" },
        { name = "PORT", value = "8001" },
        { name = "DEBUG", value = "false" }
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.database_secret_arn}:connection_string::"
        },
        {
          name      = "JWT_SECRET"
          valueFrom = "${var.app_secret_arn}:jwt_secret::"
        },
        {
          name      = "LAB_PASSWORD"
          valueFrom = "${var.app_secret_arn}:lab_password::"
        },
        {
          name      = "ADMIN_USERNAME"
          valueFrom = "${var.app_secret_arn}:admin_username::"
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = "${var.app_secret_arn}:admin_password::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "api"
  }
}

resource "aws_ecs_service" "api" {
  name            = "sima-${var.environment}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = var.use_fargate_spot ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 100
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.api_target_group_arn
    container_name   = "api"
    container_port   = 8001
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Environment = var.environment
    Service     = "api"
  }
}

# =============================================================================
# Ingest API Service (Telegram webhook)
# =============================================================================
resource "aws_ecs_task_definition" "ingest" {
  family                   = "sima-${var.environment}-ingest-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ingest_cpu
  memory                   = var.ingest_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "ingest-api"
      image = "${var.ecr_repository_urls["ingest-api"]}:${var.image_tag}"
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "HOST", value = "0.0.0.0" },
        { name = "PORT", value = "8000" },
        { name = "SQS_QUEUE_URL", value = var.sqs_queue_url }
      ]
      secrets = [
        {
          name      = "TELEGRAM_BOT_TOKEN"
          valueFrom = "${var.telegram_secret_arn}:bot_token::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ingest-api"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "ingest-api"
  }
}

resource "aws_ecs_service" "ingest" {
  name            = "sima-${var.environment}-ingest-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingest.arn
  desired_count   = var.ingest_desired_count
  launch_type     = var.use_fargate_spot ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 100
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.ingest_target_group_arn
    container_name   = "ingest-api"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Environment = var.environment
    Service     = "ingest-api"
  }
}

# =============================================================================
# Orchestrator Service (SQS worker)
# =============================================================================
resource "aws_ecs_task_definition" "orchestrator" {
  family                   = "sima-${var.environment}-orchestrator"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.orchestrator_cpu
  memory                   = var.orchestrator_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "orchestrator"
      image = "${var.ecr_repository_urls["orchestrator"]}:${var.image_tag}"
      environment = [
        { name = "SQS_QUEUE_URL", value = var.sqs_queue_url },
        { name = "S3_BUCKET", value = var.s3_bucket_name },
        { name = "MINUTE_TICK_ENABLED", value = tostring(var.minute_tick_enabled) },
        { name = "AUTONOMOUS_TICK_ENABLED", value = tostring(var.autonomous_tick_enabled) },
        { name = "TIMEZONE", value = var.orchestrator_timezone }
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.database_secret_arn}:connection_string::"
        },
        {
          name      = "TELEGRAM_BOT_TOKEN"
          valueFrom = "${var.telegram_secret_arn}:bot_token::"
        },
        {
          name      = "TELEGRAM_CHAT_ID"
          valueFrom = "${var.telegram_secret_arn}:chat_id::"
        },
        {
          name      = "OPENAI_API_KEY"
          valueFrom = "${var.llm_secret_arn}:openai_api_key::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "orchestrator"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "orchestrator"
  }
}

resource "aws_ecs_service" "orchestrator" {
  name            = "sima-${var.environment}-orchestrator"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.orchestrator.arn
  desired_count   = var.orchestrator_desired_count
  launch_type     = var.use_fargate_spot ? null : "FARGATE"

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 100
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Environment = var.environment
    Service     = "orchestrator"
  }
}

# =============================================================================
# Sleep Service (Scheduled task via EventBridge)
# =============================================================================
resource "aws_ecs_task_definition" "sleep" {
  family                   = "sima-${var.environment}-sleep"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.sleep_cpu
  memory                   = var.sleep_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "sleep"
      image = "${var.ecr_repository_urls["sleep"]}:${var.image_tag}"
      environment = [
        { name = "S3_BUCKET", value = var.s3_bucket_name }
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${var.database_secret_arn}:connection_string::"
        },
        {
          name      = "TELEGRAM_BOT_TOKEN"
          valueFrom = "${var.telegram_secret_arn}:bot_token::"
        },
        {
          name      = "OPENAI_API_KEY"
          valueFrom = "${var.llm_secret_arn}:openai_api_key::"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "sleep"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "sleep"
  }
}

# EventBridge rule for nightly sleep consolidation
resource "aws_cloudwatch_event_rule" "sleep" {
  count               = var.enable_sleep_schedule ? 1 : 0
  name                = "sima-${var.environment}-sleep-schedule"
  description         = "Trigger nightly sleep consolidation"
  schedule_expression = var.sleep_schedule

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "sleep-schedule"
  }
}

resource "aws_cloudwatch_event_target" "sleep" {
  count     = var.enable_sleep_schedule ? 1 : 0
  rule      = aws_cloudwatch_event_rule.sleep[0].name
  target_id = "sima-sleep-task"
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.sleep.arn
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [var.ecs_security_group_id]
      assign_public_ip = false
    }
  }
}

# IAM role for EventBridge to run ECS tasks
resource "aws_iam_role" "eventbridge_ecs" {
  name = "sima-${var.environment}-eventbridge-ecs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

resource "aws_iam_role_policy" "eventbridge_ecs" {
  name = "sima-${var.environment}-eventbridge-ecs"
  role = aws_iam_role.eventbridge_ecs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = aws_ecs_task_definition.sleep.arn
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_task.arn
        ]
      }
    ]
  })
}
