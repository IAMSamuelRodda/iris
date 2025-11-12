# Core Infrastructure Outputs

output "environment" {
  description = "Current environment name"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

# Lambda Function Outputs

output "agent_core_lambda_arn" {
  description = "ARN of the Agent Core Lambda function"
  value       = module.agent_core_lambda.function_arn
}

output "memory_service_lambda_arn" {
  description = "ARN of the Memory Service Lambda function"
  value       = module.memory_service_lambda.function_arn
}

output "mcp_server_lambda_arn" {
  description = "ARN of the MCP Server Lambda function"
  value       = module.mcp_server_lambda.function_arn
}

# DynamoDB Table Outputs

output "users_table_name" {
  description = "Name of the Users DynamoDB table"
  value       = module.users_table.table_name
}

output "users_table_arn" {
  description = "ARN of the Users DynamoDB table"
  value       = module.users_table.table_arn
}

output "fleets_table_name" {
  description = "Name of the Fleets DynamoDB table"
  value       = module.fleets_table.table_name
}

output "fleets_table_arn" {
  description = "ARN of the Fleets DynamoDB table"
  value       = module.fleets_table.table_arn
}

output "conversations_table_name" {
  description = "Name of the Conversations DynamoDB table"
  value       = module.conversations_table.table_name
}

output "conversations_table_arn" {
  description = "ARN of the Conversations DynamoDB table"
  value       = module.conversations_table.table_arn
}

output "memories_table_name" {
  description = "Name of the Memories DynamoDB table"
  value       = module.memories_table.table_name
}

output "memories_table_arn" {
  description = "ARN of the Memories DynamoDB table"
  value       = module.memories_table.table_arn
}

output "market_cache_table_name" {
  description = "Name of the Market Cache DynamoDB table"
  value       = module.market_cache_table.table_name
}

output "market_cache_table_arn" {
  description = "ARN of the Market Cache DynamoDB table"
  value       = module.market_cache_table.table_arn
}

output "alerts_table_name" {
  description = "Name of the Alerts DynamoDB table"
  value       = module.alerts_table.table_name
}

output "alerts_table_arn" {
  description = "ARN of the Alerts DynamoDB table"
  value       = module.alerts_table.table_arn
}

# Frontend Hosting Outputs

output "web_app_bucket_id" {
  description = "ID of the web app S3 bucket"
  value       = module.web_app_hosting.bucket_id
}

output "web_app_bucket_arn" {
  description = "ARN of the web app S3 bucket"
  value       = module.web_app_hosting.bucket_arn
}

output "web_app_cloudfront_id" {
  description = "ID of the web app CloudFront distribution"
  value       = module.web_app_hosting.cloudfront_distribution_id
}

output "web_app_cloudfront_domain" {
  description = "Domain name of the web app CloudFront distribution"
  value       = module.web_app_hosting.cloudfront_domain_name
}

output "web_app_url" {
  description = "URL to access the web application"
  value       = module.web_app_hosting.website_url
}

output "charts_bucket_id" {
  description = "ID of the charts S3 bucket (generated visualizations)"
  value       = aws_s3_bucket.charts.id
}

output "charts_bucket_arn" {
  description = "ARN of the charts S3 bucket"
  value       = aws_s3_bucket.charts.arn
}

# Future outputs:
# - API Gateway URLs
