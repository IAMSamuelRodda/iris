# Terraform State Backend Bootstrap

This directory contains the bootstrap configuration for creating the S3 bucket and DynamoDB table used for Terraform remote state management.

## ⚠️ Run Once Only

This configuration should be run **once** to create the state backend infrastructure. After creation, the main Terraform configuration will use this backend.

## Prerequisites

- AWS CLI configured with credentials
- Terraform >= 1.6.0
- Appropriate AWS permissions (S3, DynamoDB)

## Usage

### 1. Initialize and Apply Bootstrap

```bash
cd terraform/bootstrap
terraform init
terraform plan
terraform apply
```

### 2. Copy Backend Configuration

After successful apply, Terraform will output the backend configuration. Copy this to `terraform/versions.tf`:

```bash
terraform output -raw backend_config
```

### 3. Update Main Terraform Configuration

In `terraform/versions.tf`, uncomment and update the `backend "s3"` block with the values from the output.

### 4. Migrate State to Remote Backend

```bash
cd ../  # Back to terraform/
terraform init -migrate-state
```

When prompted, confirm the migration from local to remote state.

## What This Creates

### S3 Bucket
- **Name**: `star-atlas-agent-terraform-state-{region}`
- **Versioning**: Enabled (for state history)
- **Encryption**: AES256 server-side encryption
- **Public Access**: Blocked (all)

### DynamoDB Table
- **Name**: `star-atlas-agent-terraform-locks`
- **Billing**: Pay-per-request (no minimum cost)
- **Purpose**: State file locking to prevent concurrent modifications

## Cost

**Free Tier Coverage**:
- S3: < 1 MB state file (well within 5 GB free)
- DynamoDB: < 10 lock/unlock operations per deployment (within 25 WCU free)

**Estimated Cost**: $0/month (Free Tier)

## Security

- State bucket is private (all public access blocked)
- Server-side encryption enabled
- Versioning enabled for rollback capability
- DynamoDB table for atomic state locking

## Cleanup

⚠️ **Do not delete these resources** unless you're decommissioning the entire project.

If you must delete:

```bash
# 1. Migrate back to local state first
cd ../
terraform init -migrate-state  # Choose "local" backend

# 2. Then destroy bootstrap resources
cd bootstrap/
terraform destroy
```

## Troubleshooting

### "Bucket already exists"
If the bucket name is already taken globally, edit `variables.tf` and add a unique suffix to `project_name`.

### "Access Denied" during migration
Ensure your AWS credentials have permissions for:
- `s3:PutObject`, `s3:GetObject` on the state bucket
- `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:DeleteItem` on locks table
