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

variable "image_uri" {
  description = "Immutable ECR image URI, preferably repository@sha256:digest"
  type        = string
}
resource "aws_dynamodb_table" "tasks" {
  name         = "cloudops-tasks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"
  attribute {
    name = "id"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
}
resource "aws_iam_role" "api" {
  name = "cloudops-task-api-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
}
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/cloudops-task-api"
  retention_in_days = 7
}
resource "aws_iam_role_policy" "api" {
  role = aws_iam_role.api.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Scan", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.tasks.arn },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.api.arn}:*" }
  ] })
}
resource "aws_lambda_function" "api" {
  function_name                  = "cloudops-task-api"
  role                           = aws_iam_role.api.arn
  package_type                   = "Image"
  image_uri                      = var.image_uri
  architectures                  = ["x86_64"]
  memory_size                    = 128
  timeout                        = 10
  reserved_concurrent_executions = 2
  environment {
    variables = { TABLE_NAME = aws_dynamodb_table.tasks.name }
  }
  depends_on = [aws_iam_role_policy.api]
}
resource "aws_apigatewayv2_api" "api" {
  name          = "cloudops-task-api"
  protocol_type = "HTTP"
}
resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}
resource "aws_apigatewayv2_route" "api" {
  for_each           = toset(["GET /health", "POST /tasks", "GET /tasks", "GET /tasks/{id}", "PATCH /tasks/{id}", "POST /assets", "GET /assets", "GET /assets/{id}"])
  api_id             = aws_apigatewayv2_api.api.id
  route_key          = each.value
  authorization_type = "AWS_IAM"
  target             = "integrations/${aws_apigatewayv2_integration.api.id}"
}
resource "aws_apigatewayv2_stage" "api" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 5
    throttling_rate_limit  = 2
  }
}
resource "aws_lambda_permission" "gateway" {
  statement_id  = "AllowApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "cloudops-task-api-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = aws_lambda_function.api.function_name }
}
output "api_url" {
  value = aws_apigatewayv2_api.api.api_endpoint
}
