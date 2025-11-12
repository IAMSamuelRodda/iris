# Frontend Infrastructure - S3 + CloudFront

# Web App Static Hosting
module "web_app_hosting" {
  source = "./modules/s3-static-website"

  bucket_name = "${var.project_name}-web-app-${var.environment}"

  # Enable versioning for production rollback capability
  enable_versioning = var.environment == "prod" ? true : false

  # CloudFront configuration
  enable_cloudfront       = true
  cloudfront_price_class  = "PriceClass_100" # North America + Europe (cost-optimized)
  cloudfront_default_root_object = "index.html"

  # SPA routing: Redirect 404/403 to index.html for client-side routing
  cloudfront_custom_error_responses = [
    {
      error_code            = 404
      response_code         = 200
      response_page_path    = "/index.html"
      error_caching_min_ttl = 10
    },
    {
      error_code            = 403
      response_code         = 200
      response_page_path    = "/index.html"
      error_caching_min_ttl = 10
    }
  ]

  tags = {
    Component = "frontend"
    Framework = "react"
  }
}

# S3 Bucket for Generated Charts (programmatic visualizations)
# See ARCHITECTURE.md ADR-005: Programmatic Visualization for Token Efficiency
resource "aws_s3_bucket" "charts" {
  bucket = "${var.project_name}-charts-${var.environment}"

  tags = {
    Component = "charts"
    Purpose   = "generated-visualizations"
  }
}

# Block public access for charts bucket (Lambda will access with IAM)
resource "aws_s3_bucket_public_access_block" "charts" {
  bucket = aws_s3_bucket.charts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rule: Delete charts after 5 minutes (ephemeral data)
resource "aws_s3_bucket_lifecycle_configuration" "charts" {
  bucket = aws_s3_bucket.charts.id

  rule {
    id     = "delete-old-charts"
    status = "Enabled"

    expiration {
      days = 1 # Minimum allowed by AWS, effective with object tags
    }

    # Tag-based filter for 5-min TTL (set by Lambda)
    filter {
      tag {
        key   = "ttl"
        value = "short"
      }
    }
  }
}

# Server-side encryption for charts bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "charts" {
  bucket = aws_s3_bucket.charts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
