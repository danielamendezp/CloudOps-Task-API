terraform {
  required_version = ">= 1.6.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = { Project = "cloudops-task-api", ManagedBy = "Terraform", Environment = "portfolio" }
  }
}
variable "aws_region" {
  type    = string
  default = "us-east-1"
}

resource "aws_ecr_repository" "api" {
  name                 = "cloudops-task-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Keep ten latest images"
    selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
    action       = { type = "expire" }
  }] })
}
output "repository_url" {
  value = aws_ecr_repository.api.repository_url
}
