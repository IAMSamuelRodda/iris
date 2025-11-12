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

# Future outputs:
# - S3 bucket names and ARNs
# - API Gateway URLs
# - CloudFront distribution domain
