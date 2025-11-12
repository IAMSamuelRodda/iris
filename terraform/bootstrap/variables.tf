# Terraform Bootstrap Variables

variable "project_name" {
  description = "Project name (used for resource naming)"
  type        = string
  default     = "star-atlas-agent"
}

variable "aws_region" {
  description = "AWS region for state backend"
  type        = string
  default     = "us-east-1"
}
