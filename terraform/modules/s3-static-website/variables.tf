# S3 Static Website Module Variables

variable "bucket_name" {
  description = "Name of the S3 bucket (must be globally unique)"
  type        = string
}

variable "enable_versioning" {
  description = "Enable S3 versioning for rollback capability"
  type        = bool
  default     = false # Disabled by default to save costs
}

variable "enable_cloudfront" {
  description = "Enable CloudFront distribution for the bucket"
  type        = bool
  default     = true
}

variable "cloudfront_price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_100, PriceClass_200)"
  type        = string
  default     = "PriceClass_100" # North America + Europe only (cheaper)
}

variable "cloudfront_default_root_object" {
  description = "Default root object for CloudFront (SPA routing)"
  type        = string
  default     = "index.html"
}

variable "cloudfront_custom_error_responses" {
  description = "Custom error responses for SPA routing"
  type = list(object({
    error_code            = number
    response_code         = number
    response_page_path    = string
    error_caching_min_ttl = number
  }))
  default = [
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
}

variable "tags" {
  description = "Additional tags for the bucket and distribution"
  type        = map(string)
  default     = {}
}
