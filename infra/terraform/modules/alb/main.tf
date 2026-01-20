# ALB module for SIMA services

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "sima-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.security_group_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = {
    Name        = "sima-${var.environment}-alb"
    Environment = var.environment
    Service     = "sima"
  }
}

# HTTPS Listener (primary)
resource "aws_lb_listener" "https" {
  count             = var.certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# HTTP Listener (redirect to HTTPS or forward if no certificate)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  dynamic "default_action" {
    for_each = var.certificate_arn != "" ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.certificate_arn == "" ? [1] : []
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.web.arn
    }
  }
}

# =============================================================================
# Target Groups
# =============================================================================

# Web Target Group (Next.js)
resource "aws_lb_target_group" "web" {
  name        = "sima-${var.environment}-web"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200-399"
  }

  tags = {
    Name        = "sima-${var.environment}-web-tg"
    Environment = var.environment
    Service     = "web"
  }
}

# API Target Group (FastAPI)
resource "aws_lb_target_group" "api" {
  name        = "sima-${var.environment}-api"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name        = "sima-${var.environment}-api-tg"
    Environment = var.environment
    Service     = "api"
  }
}

# Ingest API Target Group (Telegram webhook)
resource "aws_lb_target_group" "ingest" {
  name        = "sima-${var.environment}-ingest"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name        = "sima-${var.environment}-ingest-tg"
    Environment = var.environment
    Service     = "ingest-api"
  }
}

# =============================================================================
# Listener Rules (Path-based routing)
# =============================================================================

# API path rule - split into multiple rules due to 5 pattern limit
resource "aws_lb_listener_rule" "api" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/traces/*", "/events/*", "/memories/*", "/metrics/*", "/admin/*"]
    }
  }
}

resource "aws_lb_listener_rule" "api2" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 101

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/auth/*", "/ws/*", "/health"]
    }
  }
}

# Ingest path rule (/ingest/*)
resource "aws_lb_listener_rule" "ingest" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ingest.arn
  }

  condition {
    path_pattern {
      values = ["/ingest/*", "/webhook/*"]
    }
  }
}
