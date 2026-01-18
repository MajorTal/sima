# EventBridge rules for SIMA time-based triggers

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue to send events to"
  type        = string
}

variable "sqs_queue_url" {
  description = "URL of the SQS queue to send events to"
  type        = string
}

variable "minute_tick_enabled" {
  description = "Enable minute tick events"
  type        = bool
  default     = false
}

variable "autonomous_tick_enabled" {
  description = "Enable autonomous tick events"
  type        = bool
  default     = false
}

variable "autonomous_tick_rate" {
  description = "Rate expression for autonomous tick (e.g., 'rate(10 minutes)')"
  type        = string
  default     = "rate(10 minutes)"
}

# Minute Tick Rule - Every minute
resource "aws_cloudwatch_event_rule" "minute_tick" {
  count               = var.minute_tick_enabled ? 1 : 0
  name                = "sima-${var.environment}-minute-tick"
  description         = "Triggers every minute for SIMA time awareness"
  schedule_expression = "rate(1 minute)"
  state               = "ENABLED"

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "minute-tick"
  }
}

resource "aws_cloudwatch_event_target" "minute_tick_sqs" {
  count     = var.minute_tick_enabled ? 1 : 0
  rule      = aws_cloudwatch_event_rule.minute_tick[0].name
  target_id = "sima-minute-tick-sqs"
  arn       = var.sqs_queue_arn

  input = jsonencode({
    event_type = "minute_tick"
    source     = "eventbridge"
  })
}

# Autonomous Tick Rule - Configurable rate
resource "aws_cloudwatch_event_rule" "autonomous_tick" {
  count               = var.autonomous_tick_enabled ? 1 : 0
  name                = "sima-${var.environment}-autonomous-tick"
  description         = "Triggers periodically for SIMA autonomous thinking"
  schedule_expression = var.autonomous_tick_rate
  state               = "ENABLED"

  tags = {
    Environment = var.environment
    Service     = "sima"
    Purpose     = "autonomous-tick"
  }
}

resource "aws_cloudwatch_event_target" "autonomous_tick_sqs" {
  count     = var.autonomous_tick_enabled ? 1 : 0
  rule      = aws_cloudwatch_event_rule.autonomous_tick[0].name
  target_id = "sima-autonomous-tick-sqs"
  arn       = var.sqs_queue_arn

  input = jsonencode({
    event_type = "autonomous_tick"
    source     = "eventbridge"
  })
}

# IAM policy for EventBridge to send to SQS
resource "aws_sqs_queue_policy" "eventbridge_to_sqs" {
  count     = (var.minute_tick_enabled || var.autonomous_tick_enabled) ? 1 : 0
  queue_url = var.sqs_queue_url

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowEventBridgeToSendMessage"
        Effect    = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = var.sqs_queue_arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = concat(
              var.minute_tick_enabled ? [aws_cloudwatch_event_rule.minute_tick[0].arn] : [],
              var.autonomous_tick_enabled ? [aws_cloudwatch_event_rule.autonomous_tick[0].arn] : []
            )
          }
        }
      }
    ]
  })
}

# Outputs
output "minute_tick_rule_arn" {
  description = "ARN of the minute tick EventBridge rule"
  value       = var.minute_tick_enabled ? aws_cloudwatch_event_rule.minute_tick[0].arn : null
}

output "autonomous_tick_rule_arn" {
  description = "ARN of the autonomous tick EventBridge rule"
  value       = var.autonomous_tick_enabled ? aws_cloudwatch_event_rule.autonomous_tick[0].arn : null
}
