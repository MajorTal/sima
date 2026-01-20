# Variables for ECR module

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
}

variable "scan_on_push" {
  description = "Enable image scanning on push"
  type        = bool
  default     = true
}

variable "image_retention_count" {
  description = "Number of tagged images to retain"
  type        = number
  default     = 10
}

variable "untagged_image_days" {
  description = "Days to retain untagged images"
  type        = number
  default     = 7
}
