# ECR module for SIMA container repositories

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  services = ["web", "api", "ingest-api", "orchestrator", "sleep"]
}

# ECR Repositories for each service
resource "aws_ecr_repository" "services" {
  for_each = toset(local.services)

  name                 = "sima-${var.environment}/${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = "sima-${var.environment}-${each.key}"
    Environment = var.environment
    Service     = each.key
  }
}

# Lifecycle policy for each repository
resource "aws_ecr_lifecycle_policy" "services" {
  for_each   = toset(local.services)
  repository = aws_ecr_repository.services[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.image_retention_count} images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = var.image_retention_count
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images after ${var.untagged_image_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_image_days
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# IAM policy for pushing images
data "aws_iam_policy_document" "push_images" {
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:GetRepositoryPolicy",
      "ecr:DescribeRepositories",
      "ecr:ListImages",
      "ecr:DescribeImages",
      "ecr:BatchGetImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage"
    ]
    resources = [for repo in aws_ecr_repository.services : repo.arn]
  }
}

resource "aws_iam_policy" "push_images" {
  name        = "sima-${var.environment}-ecr-push"
  description = "Policy to push images to SIMA ECR repositories"
  policy      = data.aws_iam_policy_document.push_images.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}

# IAM policy for pulling images
data "aws_iam_policy_document" "pull_images" {
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage"
    ]
    resources = [for repo in aws_ecr_repository.services : repo.arn]
  }
}

resource "aws_iam_policy" "pull_images" {
  name        = "sima-${var.environment}-ecr-pull"
  description = "Policy to pull images from SIMA ECR repositories"
  policy      = data.aws_iam_policy_document.pull_images.json

  tags = {
    Environment = var.environment
    Service     = "sima"
  }
}
