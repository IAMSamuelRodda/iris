# DynamoDB Table Module Outputs

output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.this.arn
}

output "table_id" {
  description = "ID of the DynamoDB table"
  value       = aws_dynamodb_table.this.id
}

output "stream_arn" {
  description = "ARN of the DynamoDB stream (if enabled)"
  value       = var.stream_enabled ? aws_dynamodb_table.this.stream_arn : null
}

output "stream_label" {
  description = "Label of the DynamoDB stream (if enabled)"
  value       = var.stream_enabled ? aws_dynamodb_table.this.stream_label : null
}
