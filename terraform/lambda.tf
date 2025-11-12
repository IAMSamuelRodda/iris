# Lambda Functions Configuration

# Agent Core - Claude Agent SDK orchestrator
module "agent_core_lambda" {
  source = "./modules/lambda"

  function_name = "${var.project_name}-agent-core-${var.environment}"
  description   = "Claude Agent SDK orchestrator for Star Atlas Agent"
  runtime       = "nodejs20.x"
  handler       = "index.handler"
  memory_size   = 1024  # Needs more memory for Claude Agent SDK
  timeout       = 60    # Agent processing can take longer

  source_dir = "${path.root}/../packages/agent-core/lambda-placeholder"

  environment_variables = {
    ENVIRONMENT    = var.environment
    NODE_ENV       = var.environment == "prod" ? "production" : "development"
    LOG_LEVEL      = var.environment == "prod" ? "info" : "debug"
    # ANTHROPIC_API_KEY will be added via Secrets Manager in later implementation
  }

  policy_statements = [
    {
      effect = "Allow"
      actions = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ]
      resources = ["*"]  # Will be scoped to specific models later
    },
    {
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ]
      resources = ["*"]  # Will be scoped to specific tables after DynamoDB setup
    }
  ]

  tags = {
    Function = "agent-core"
    Runtime  = "nodejs20"
  }
}

# Memory Service - RAG + vector search
module "memory_service_lambda" {
  source = "./modules/lambda"

  function_name = "${var.project_name}-memory-${var.environment}"
  description   = "RAG and vector search service for user memory"
  runtime       = "nodejs20.x"
  handler       = "index.handler"
  memory_size   = 512
  timeout       = 30

  source_dir = "${path.root}/../packages/memory-service/lambda-placeholder"

  environment_variables = {
    ENVIRONMENT = var.environment
    NODE_ENV    = var.environment == "prod" ? "production" : "development"
    LOG_LEVEL   = var.environment == "prod" ? "info" : "debug"
  }

  policy_statements = [
    {
      effect = "Allow"
      actions = [
        "bedrock:InvokeModel"  # For Titan embeddings
      ]
      resources = ["*"]
    },
    {
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem"
      ]
      resources = ["*"]  # Will be scoped to memories table later
    }
  ]

  tags = {
    Function = "memory-service"
    Runtime  = "nodejs20"
  }
}

# MCP Server - Star Atlas & Solana integration
module "mcp_server_lambda" {
  source = "./modules/lambda"

  function_name = "${var.project_name}-mcp-server-${var.environment}"
  description   = "MCP tools for Star Atlas and Solana blockchain"
  runtime       = "nodejs20.x"
  handler       = "index.handler"
  memory_size   = 512
  timeout       = 30

  source_dir = "${path.root}/../packages/mcp-staratlas-server/lambda-placeholder"

  environment_variables = {
    ENVIRONMENT      = var.environment
    NODE_ENV         = var.environment == "prod" ? "production" : "development"
    LOG_LEVEL        = var.environment == "prod" ? "info" : "debug"
    # SOLANA_RPC_URL will be added later
    # HELIUS_API_KEY will be added via Secrets Manager
  }

  policy_statements = [
    {
      effect = "Allow"
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query"
      ]
      resources = ["*"]  # Will be scoped to market_cache and fleets tables
    }
  ]

  tags = {
    Function = "mcp-server"
    Runtime  = "nodejs20"
  }
}
