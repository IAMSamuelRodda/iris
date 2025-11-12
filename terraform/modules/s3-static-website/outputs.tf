# S3 Static Website Module Outputs

output "bucket_id" {
  description = "ID of the S3 bucket"
  value       = aws_s3_bucket.website.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.website.arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = aws_s3_bucket.website.bucket_regional_domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution (if enabled)"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.website[0].id : null
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution (if enabled)"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.website[0].arn : null
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution (if enabled)"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.website[0].domain_name : null
}

output "website_url" {
  description = "URL to access the website (CloudFront if enabled, else S3)"
  value       = var.enable_cloudfront ? "https://${aws_cloudfront_distribution.website[0].domain_name}" : "https://${aws_s3_bucket.website.bucket_regional_domain_name}"
}
