terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state management
  # After running terraform/bootstrap/, uncomment and configure:
  # backend "s3" {
  #   bucket         = "star-atlas-agent-terraform-state-{region}"
  #   key            = "terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "star-atlas-agent-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "star-atlas-agent"
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "https://github.com/IAMSamuelRodda/star-atlas-agent"
    }
  }
}
