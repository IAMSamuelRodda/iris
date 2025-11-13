# Authentication Service Infrastructure

# DynamoDB Table: Magic Link Tokens
resource "aws_dynamodb_table" "magic_link_tokens" {
  name         = "${var.project_name}-tokens-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "token"

  attribute {
    name = "token"
    type = "S"
  }

  # TTL for automatic cleanup of expired tokens
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-tokens-${var.environment}"
  })
}

# DynamoDB Table: Users
resource "aws_dynamodb_table" "users" {
  name         = "${var.project_name}-users-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "walletAddress"
    type = "S"
  }

  # GSI for looking up users by email (for magic link auth)
  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
  }

  # GSI for looking up users by wallet address (for wallet auth)
  global_secondary_index {
    name            = "WalletAddressIndex"
    hash_key        = "walletAddress"
    projection_type = "ALL"
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-users-${var.environment}"
  })
}

# DynamoDB Table: Wallet Challenges
resource "aws_dynamodb_table" "wallet_challenges" {
  name         = "${var.project_name}-challenges-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "challengeId"

  attribute {
    name = "challengeId"
    type = "S"
  }

  attribute {
    name = "walletAddress"
    type = "S"
  }

  # GSI for looking up challenges by wallet address
  global_secondary_index {
    name            = "WalletAddressIndex"
    hash_key        = "walletAddress"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup of expired challenges
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-challenges-${var.environment}"
  })
}

# DynamoDB Table: Rate Limiting
resource "aws_dynamodb_table" "rate_limits" {
  name         = "${var.project_name}-rate-limits-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "key"

  attribute {
    name = "key"
    type = "S"
  }

  # TTL for automatic cleanup of expired rate limit records
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-rate-limits-${var.environment}"
  })
}

# Lambda Module: Auth Service
module "auth_service_lambda" {
  source = "./modules/lambda"

  function_name = "${var.project_name}-auth-service-${var.environment}"
  description   = "Authentication service with magic link and JWT"
  handler       = "index.handler"
  runtime       = "nodejs20.x"
  timeout       = 30
  memory_size   = 512

  source_dir = "${path.root}/../packages/auth-service/lambda-placeholder"

  environment_variables = {
    TOKENS_TABLE      = aws_dynamodb_table.magic_link_tokens.name
    USERS_TABLE       = aws_dynamodb_table.users.name
    CHALLENGES_TABLE  = aws_dynamodb_table.wallet_challenges.name
    RATE_LIMIT_TABLE  = aws_dynamodb_table.rate_limits.name
    FRONTEND_URL      = var.environment == "prod" ? "https://staratlas-agent.com" : "http://localhost:5173"
    FROM_EMAIL        = var.environment == "prod" ? "noreply@staratlas-agent.com" : "noreply@staratlas-agent.com"
    JWT_SECRET        = var.jwt_secret
  }

  tags = var.tags
}

# IAM Policy: DynamoDB Access for Auth Lambda
resource "aws_iam_role_policy" "auth_lambda_dynamodb" {
  name = "${var.project_name}-auth-lambda-dynamodb-${var.environment}"
  role = module.auth_service_lambda.role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.magic_link_tokens.arn,
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          aws_dynamodb_table.wallet_challenges.arn,
          "${aws_dynamodb_table.wallet_challenges.arn}/index/*",
          aws_dynamodb_table.rate_limits.arn
        ]
      }
    ]
  })
}

# IAM Policy: SES Email Sending for Auth Lambda
resource "aws_iam_role_policy" "auth_lambda_ses" {
  name = "${var.project_name}-auth-lambda-ses-${var.environment}"
  role = module.auth_service_lambda.role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = var.environment == "prod" ? "noreply@staratlas-agent.com" : "noreply@staratlas-agent.com"
          }
        }
      }
    ]
  })
}

# API Gateway Integration: Auth Service
resource "aws_apigatewayv2_integration" "auth_service" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"

  connection_type        = "INTERNET"
  description            = "Auth Service Lambda integration"
  integration_method     = "POST"
  integration_uri        = module.auth_service_lambda.invoke_arn
  payload_format_version = "2.0"
}

# API Gateway Routes: Auth Endpoints
resource "aws_apigatewayv2_route" "auth_send_magic_link" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/magic-link"
  target    = "integrations/${aws_apigatewayv2_integration.auth_service.id}"
}

resource "aws_apigatewayv2_route" "auth_verify_magic_link" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/verify"
  target    = "integrations/${aws_apigatewayv2_integration.auth_service.id}"
}

resource "aws_apigatewayv2_route" "auth_wallet_challenge" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/wallet/challenge"
  target    = "integrations/${aws_apigatewayv2_integration.auth_service.id}"
}

resource "aws_apigatewayv2_route" "auth_wallet_verify" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth/wallet/verify"
  target    = "integrations/${aws_apigatewayv2_integration.auth_service.id}"
}

resource "aws_apigatewayv2_route" "profile_get" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /profile"
  target    = "integrations/${aws_apigatewayv2_integration.auth_service.id}"
}

resource "aws_apigatewayv2_route" "profile_update" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "PUT /profile"
  target    = "integrations/${aws_apigatewayv2_integration.auth_service.id}"
}

# Lambda Permission: API Gateway Invoke
resource "aws_lambda_permission" "auth_service_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.auth_service_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
