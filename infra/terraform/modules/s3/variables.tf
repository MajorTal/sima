# Variables for S3 module

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID for bucket naming"
  type        = string
}

variable "enable_versioning" {
  description = "Enable S3 versioning"
  type        = bool
  default     = true
}

variable "retention_days" {
  description = "Days to retain objects before expiration"
  type        = number
  default     = 365
}
