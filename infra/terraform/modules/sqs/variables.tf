# Variables for SQS module

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "visibility_timeout" {
  description = "Visibility timeout in seconds"
  type        = number
  default     = 300  # 5 minutes for processing
}

variable "message_retention_seconds" {
  description = "Message retention period in seconds"
  type        = number
  default     = 345600  # 4 days
}

variable "receive_wait_time" {
  description = "Long polling wait time in seconds"
  type        = number
  default     = 20
}

variable "max_receive_count" {
  description = "Max receive count before sending to DLQ"
  type        = number
  default     = 3
}
