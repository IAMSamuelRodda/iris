# Lambda Function Terraform Module

Reusable Terraform module for creating AWS Lambda functions with best practices.

## Features

- ✅ Automatic code packaging (ZIP)
- ✅ IAM role creation with least privilege
- ✅ CloudWatch Logs with configurable retention
- ✅ VPC support (optional)
- ✅ Custom IAM policies (inline + managed)
- ✅ Lambda layers support
- ✅ Environment variables
- ✅ Configurable memory, timeout, and concurrency

## Usage

```hcl
module "my_lambda" {
  source = "./modules/lambda"

  function_name = "my-function"
  description   = "My Lambda function"
  runtime       = "nodejs20.x"
  handler       = "index.handler"
  memory_size   = 512
  timeout       = 30

  source_dir = "../path/to/lambda/code"

  environment_variables = {
    ENV_VAR_1 = "value1"
    ENV_VAR_2 = "value2"
  }

  policy_statements = [
    {
      effect    = "Allow"
      actions   = ["dynamodb:GetItem"]
      resources = ["arn:aws:dynamodb:*:*:table/my-table"]
    }
  ]

  tags = {
    Application = "my-app"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| function_name | Name of the Lambda function | string | - | yes |
| description | Description of the function | string | "" | no |
| runtime | Lambda runtime | string | "nodejs20.x" | no |
| handler | Function handler | string | "index.handler" | no |
| memory_size | Memory in MB (128-10240) | number | 512 | no |
| timeout | Timeout in seconds (1-900) | number | 30 | no |
| source_dir | Path to source code directory | string | - | yes |
| environment_variables | Environment variables | map(string) | {} | no |
| layers | Lambda layer ARNs | list(string) | [] | no |
| vpc_config | VPC configuration | object | null | no |
| reserved_concurrent_executions | Reserved concurrent executions | number | -1 | no |
| attach_policy_arns | IAM policy ARNs to attach | list(string) | [] | no |
| policy_statements | Custom IAM policy statements | list(object) | [] | no |
| tags | Additional tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| function_name | Name of the Lambda function |
| function_arn | ARN of the Lambda function |
| invoke_arn | Invoke ARN (for API Gateway) |
| role_arn | ARN of the execution role |
| role_name | Name of the execution role |
| log_group_name | Name of the CloudWatch log group |
| qualified_arn | Qualified ARN (with version) |

## IAM Permissions

The module automatically attaches:
- `AWSLambdaBasicExecutionRole` - CloudWatch Logs access
- `AWSLambdaVPCAccessExecutionRole` - VPC access (if vpc_config is provided)

Custom permissions can be added via:
- `attach_policy_arns` - For AWS managed or custom policy ARNs
- `policy_statements` - For inline policy statements

## Best Practices

1. **Memory Sizing**: Start with 512 MB, adjust based on performance metrics
2. **Timeout**: Keep as low as possible, max 900 seconds (15 minutes)
3. **Concurrent Executions**: Use reserved concurrency to prevent runaway costs
4. **Environment Variables**: Never store secrets directly - use Secrets Manager or Parameter Store
5. **VPC**: Only use VPC if accessing private resources (adds cold start latency)
6. **Layers**: Use layers for shared dependencies across multiple functions

## Examples

### With DynamoDB Access

```hcl
module "my_lambda" {
  source = "./modules/lambda"

  function_name = "my-dynamodb-function"
  source_dir    = "../packages/my-service/lambda"

  policy_statements = [
    {
      effect    = "Allow"
      actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"]
      resources = [aws_dynamodb_table.my_table.arn]
    }
  ]
}
```

### With VPC

```hcl
module "my_lambda" {
  source = "./modules/lambda"

  function_name = "my-vpc-function"
  source_dir    = "../packages/my-service/lambda"

  vpc_config = {
    subnet_ids         = module.vpc.private_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }
}
```

### With Secrets Manager

```hcl
module "my_lambda" {
  source = "./modules/lambda"

  function_name = "my-secret-function"
  source_dir    = "../packages/my-service/lambda"

  attach_policy_arns = [
    aws_iam_policy.secrets_manager_read.arn
  ]

  environment_variables = {
    SECRET_ARN = aws_secretsmanager_secret.my_secret.arn
  }
}
```

## Notes

- Lambda code is packaged automatically using `archive_file` data source
- CloudWatch log retention is set to 7 days by default (adjust in main.tf)
- The module creates a unique IAM role per function for security isolation
