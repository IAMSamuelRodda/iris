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

# Future outputs:
# - S3 bucket names and ARNs
# - DynamoDB table names and ARNs
# - API Gateway URLs
# - CloudFront distribution domain
