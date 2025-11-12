# DynamoDB Tables Configuration

# Users Table - User profiles, authentication, relationship progression
module "users_table" {
  source = "./modules/dynamodb-table"

  table_name = "${var.project_name}-users-${var.environment}"
  hash_key   = "user_id"

  attributes = [
    { name = "user_id", type = "S" },
    { name = "email", type = "S" },
    { name = "wallet_address", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "email-index"
      hash_key        = "email"
      range_key       = null
      projection_type = "ALL"
    },
    {
      name            = "wallet-index"
      hash_key        = "wallet_address"
      range_key       = null
      projection_type = "ALL"
    }
  ]

  point_in_time_recovery = true

  tags = {
    Table = "users"
    Data  = "user-profiles"
  }
}

# Fleets Table - Fleet configurations and state
module "fleets_table" {
  source = "./modules/dynamodb-table"

  table_name = "${var.project_name}-fleets-${var.environment}"
  hash_key   = "fleet_id"

  attributes = [
    { name = "fleet_id", type = "S" },
    { name = "user_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "user-fleets-index"
      hash_key        = "user_id"
      range_key       = null
      projection_type = "ALL"
    }
  ]

  point_in_time_recovery = true

  tags = {
    Table = "fleets"
    Data  = "fleet-configurations"
  }
}

# Conversations Table - Recent chat history (48-hour TTL)
module "conversations_table" {
  source = "./modules/dynamodb-table"

  table_name = "${var.project_name}-conversations-${var.environment}"
  hash_key   = "conversation_id"

  attributes = [
    { name = "conversation_id", type = "S" },
    { name = "user_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "user-conversations-index"
      hash_key        = "user_id"
      range_key       = null
      projection_type = "ALL"
    }
  ]

  ttl_enabled        = true
  ttl_attribute_name = "ttl" # Expiration timestamp (48 hours)

  point_in_time_recovery = false # Not needed for ephemeral data

  tags = {
    Table = "conversations"
    Data  = "chat-history-ttl"
  }
}

# Memories Table - Vector embeddings for long-term personalization
module "memories_table" {
  source = "./modules/dynamodb-table"

  table_name = "${var.project_name}-memories-${var.environment}"
  hash_key   = "memory_id"

  attributes = [
    { name = "memory_id", type = "S" },
    { name = "user_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "user-memories-index"
      hash_key        = "user_id"
      range_key       = null
      projection_type = "ALL"
    }
  ]

  point_in_time_recovery = true # Important for user data

  tags = {
    Table = "memories"
    Data  = "vector-embeddings"
  }
}

# Market Cache Table - Price data (5-min TTL)
module "market_cache_table" {
  source = "./modules/dynamodb-table"

  table_name = "${var.project_name}-market-cache-${var.environment}"
  hash_key   = "asset_id"

  attributes = [
    { name = "asset_id", type = "S" }
  ]

  ttl_enabled        = true
  ttl_attribute_name = "ttl" # Expiration timestamp (5 minutes)

  point_in_time_recovery = false # Not needed for cache data

  tags = {
    Table = "market-cache"
    Data  = "price-data-ttl"
  }
}

# Alerts Table - Active user alerts
module "alerts_table" {
  source = "./modules/dynamodb-table"

  table_name = "${var.project_name}-alerts-${var.environment}"
  hash_key   = "alert_id"

  attributes = [
    { name = "alert_id", type = "S" },
    { name = "user_id", type = "S" },
    { name = "fleet_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "user-alerts-index"
      hash_key        = "user_id"
      range_key       = null
      projection_type = "ALL"
    },
    {
      name            = "fleet-alerts-index"
      hash_key        = "fleet_id"
      range_key       = null
      projection_type = "ALL"
    }
  ]

  point_in_time_recovery = true

  tags = {
    Table = "alerts"
    Data  = "active-notifications"
  }
}
