---
name: terraform-iac-expert
description: Best practices for writing and reviewing Terraform / Infrastructure as Code across AWS, Azure, and GCP
---

# Terraform & Infrastructure as Code Expert

A deep Terraform/IaC best-practices skill for writing and reviewing infrastructure across AWS, Azure, and GCP. It layers IaC-specific deltas (state, providers, modules, secrets, cloud patterns) on top of the injected universal style core, and drives the `/terraform-review` command with a structured report and a standardized severity scale.

## When to Use / When NOT to Use

Use this skill when:

- Writing or reviewing Terraform configurations (`.tf`, `.tfvars`)
- Designing cloud infrastructure across AWS, Azure, or GCP
- Creating or versioning reusable Terraform modules
- Debugging Terraform state or deployment issues
- Setting up CI/CD pipelines for infrastructure
- Implementing security and compliance best practices for IaC

Do NOT use this skill when:

- The IaC is not Terraform/HCL (raw CloudFormation, Pulumi, Ansible, CDK). The state, provider, and module guidance here is Terraform-specific.
- You are reviewing application code rather than infrastructure definitions. Use the matching language style skill instead.
- The change is a one-off `terraform import` or state inspection with no configuration change to review.

## Universal Core (injected)

The universal style core in `hooks/style-core.md` (TRUE code plus the 9 principles) is injected separately every session; do not restate it. It maps cleanly onto Terraform: prefer small single-purpose modules (small units); wait for real duplication before extracting a module or `locals` block (DRY without premature abstraction); keep module interfaces simple and fail fast with typed input variables, `validation` blocks, and explicit `sensitive` flags (simple interfaces plus fail fast); and let descriptive variable names and `description` fields do the documenting (names do the documenting). The sections below are the IaC-specific deltas only.

## Terraform Principles

### Architecture & Modularity

- Infrastructure as Code first: every resource is declared, version-controlled, and reproducible.
- Build modular, reusable, single-responsibility modules; break infrastructure into logical units (networking, compute, storage).
- Treat infrastructure as immutable: replace rather than mutate in place.
- Security by default with least-privilege access across all three clouds.
- Isolate environments via separate state and/or workspaces.

Key principles:

1. **Modularity**: Break infrastructure into logical, reusable modules.
2. **Immutability**: Treat infrastructure as immutable; replace rather than modify.
3. **Version Control**: Everything in Git with semantic versioning.
4. **State Management**: Remote backends with locking and encryption.
5. **Documentation**: Self-documenting code with clear variable descriptions.

### Code Organization & File Structure

Organize a project by environment and module:

```text
project/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
├── modules/
│   ├── networking/
│   ├── compute/
│   └── storage/
├── shared/
│   ├── backend.tf
│   └── providers.tf
└── README.md
```

Standard file roles within a module or root:

- `main.tf`: Primary resource definitions
- `variables.tf`: Input variable declarations with validation
- `outputs.tf`: Output values for module consumers
- `versions.tf`: Provider and Terraform version constraints
- `backend.tf`: Remote state configuration
- `locals.tf`: Local values and computed variables
- `data.tf`: Data source queries

Code quality hygiene:

- Always run `terraform fmt` before committing.
- Use `terraform validate` to catch syntax errors.
- Run `tflint` or `terrascan` for additional validation.
- Use `terraform-docs` to auto-generate module documentation.
- Set up pre-commit hooks for automated checks.

Input variables should be typed, described, and validated:

```hcl
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "instance_count" {
  description = "Number of instances to create"
  type        = number
  default     = 1

  validation {
    condition     = var.instance_count > 0 && var.instance_count <= 10
    error_message = "Instance count must be between 1 and 10."
  }
}
```

### State Management

- **Always** use remote backends (S3, Azure Blob, GCS, Terraform Cloud).
- Enable state locking (DynamoDB for S3, native for others).
- Enable encryption at rest for state files.
- Use workspaces for environment separation.
- Never commit state files to version control.

```hcl
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### Provider Version Locking

Pin both Terraform and every provider so plans are reproducible:

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}
```

### Module Development & Versioning

Every module should have:

- A clear, single responsibility
- Well-defined inputs with validation
- Documented outputs
- Examples in an `examples/` directory
- Tests in a `tests/` directory
- A comprehensive `README.md`

Versioning rules:

- Use semantic versioning (MAJOR.MINOR.PATCH).
- Tag releases in Git.
- Document breaking changes in `CHANGELOG.md`.
- Reference modules by version tag, never by branch.

```hcl
module "vpc" {
  source = "git::https://github.com/org/terraform-modules.git//vpc?ref=v2.1.0"

  name        = "production-vpc"
  cidr_block  = "10.0.0.0/16"
  environment = var.environment
  enable_nat  = true
}
```

Outputs should be described so consumers can wire modules together:

```hcl
output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}
```

Document each module with a consistent README so inputs and outputs are discoverable:

````markdown
# Module Name

## Overview

Brief description of what the module does.

## Requirements

- Terraform >= 1.6.0
- AWS Provider >= 5.0

## Usage

```hcl
module "example" {
  source = "./modules/example"

  name        = "my-resource"
  environment = "prod"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| name | Resource name | string | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| id | Resource ID |

## Examples

See `examples/` directory for complete examples.
````

### Security

#### Secrets Management

- **NEVER** hardcode secrets or credentials.
- Use AWS Secrets Manager, Azure Key Vault, or GCP Secret Manager.
- Use environment variables for CI/CD pipelines.
- Integrate with HashiCorp Vault for dynamic credentials.
- Mark sensitive variables and outputs with `sensitive = true`.

```hcl
variable "database_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

output "db_connection_string" {
  description = "Database connection string"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}
```

#### Resource Security

- Enable encryption by default (at rest and in transit).
- Use private subnets for backend resources.
- Implement least-privilege IAM policies.
- Enable logging and monitoring (CloudTrail, Azure Monitor, Cloud Audit Logs).
- Use security groups and NACLs restrictively.
- Enable MFA for sensitive operations.

#### Tagging Strategy

Centralize common tags in `locals` and merge per-resource overrides:

```hcl
locals {
  common_tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = var.project_name
    CostCenter  = var.cost_center
    Owner       = var.owner_email
  }
}

resource "aws_instance" "web" {
  # ... other configuration ...

  tags = merge(
    local.common_tags,
    {
      Name = "web-server-${var.environment}"
      Role = "web"
    }
  )
}
```

### Error Handling

Use conditional resources for optional infrastructure:

```hcl
resource "aws_instance" "optional" {
  count = var.create_instance ? 1 : 0

  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
}
```

Guard nullable inputs with explicit defaults:

```hcl
locals {
  vpc_id = var.vpc_id != null ? var.vpc_id : aws_vpc.main[0].id

  subnet_ids = var.subnet_ids != null ? var.subnet_ids : aws_subnet.main[*].id
}
```

Make ordering explicit with `depends_on` where Terraform cannot infer it:

```hcl
resource "aws_eip" "nat" {
  depends_on = [aws_internet_gateway.main]

  domain = "vpc"
  tags   = local.common_tags
}
```

### Testing & Validation

Unit-test modules with Terratest:

```go
// Example Terratest structure
func TestTerraformVPC(t *testing.T) {
    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../examples/vpc",
    })

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    vpcID := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcID)
}
```

Layer validation checks:

- Syntax validation: `terraform validate`
- Formatting: `terraform fmt -check`
- Security scanning: `tfsec`, `checkov`, `terrascan`
- Policy as code: Sentinel, OPA
- Cost estimation: Infracost

### CI/CD Integration

GitHub Actions:

```yaml
name: Terraform CI

on:
  pull_request:
    paths:
      - '**.tf'
      - '**.tfvars'

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Terraform Format
        run: terraform fmt -check -recursive

      - name: Terraform Init
        run: terraform init -backend=false

      - name: Terraform Validate
        run: terraform validate

      - name: TFLint
        uses: terraform-linters/setup-tflint@v4

      - name: Run TFLint
        run: tflint --recursive

      - name: Terraform Plan
        run: terraform plan -no-color
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

GitLab CI:

```yaml
stages:
  - validate
  - plan
  - apply

variables:
  TF_VERSION: "1.6.0"

.terraform-base:
  image: hashicorp/terraform:$TF_VERSION
  before_script:
    - terraform init

validate:
  extends: .terraform-base
  stage: validate
  script:
    - terraform fmt -check
    - terraform validate

plan:
  extends: .terraform-base
  stage: plan
  script:
    - terraform plan -out=tfplan
  artifacts:
    paths:
      - tfplan

apply:
  extends: .terraform-base
  stage: apply
  script:
    - terraform apply tfplan
  when: manual
  only:
    - main
```

### Performance

Target specific resources to scope large applies:

```bash
# Apply changes to specific resources
terraform apply -target=module.vpc -target=aws_instance.web

# Plan for specific resources
terraform plan -target=module.database
```

Tune parallelism to the provider's rate limits:

```bash
# Increase parallelism for faster operations
terraform apply -parallelism=20

# Reduce for rate-limited APIs
terraform apply -parallelism=5
```

Cache provider plugins across runs:

```bash
# Set plugin cache directory
export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"
mkdir -p $TF_PLUGIN_CACHE_DIR
```

Prefer `for_each` over `count` so resource identity is stable when the collection changes:

```hcl
# Prefer for_each over count for maps
resource "aws_instance" "servers" {
  for_each = var.server_config

  ami           = each.value.ami
  instance_type = each.value.instance_type

  tags = {
    Name = each.key
  }
}

# Use for_each for sets
resource "aws_subnet" "private" {
  for_each = toset(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, index(var.availability_zones, each.value))
}
```

### Cloud-Specific Patterns

AWS:

- Use VPC endpoints for AWS services.
- Implement multi-AZ deployments.
- Use Auto Scaling Groups for resilience.
- Enable CloudWatch logging and monitoring.
- Use Systems Manager for parameter storage.

Azure:

- Use Resource Groups for logical organization.
- Implement Azure Policy for governance.
- Use Managed Identities for authentication.
- Enable Azure Monitor and Log Analytics.
- Use Azure Key Vault for secrets.

GCP:

- Use Projects for isolation.
- Implement Organization Policies.
- Use Service Accounts with minimal permissions.
- Enable Cloud Logging and Monitoring.
- Use Secret Manager for sensitive data.

### Common Patterns

Dynamic blocks for repeated nested configuration:

```hcl
resource "aws_security_group" "main" {
  name        = var.name
  description = var.description
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
    }
  }
}
```

Data sources to reference existing infrastructure:

```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
```

Locals for computed values:

```hcl
locals {
  # Compute subnet CIDR blocks
  private_subnets = [
    for idx, az in var.availability_zones :
    cidrsubnet(var.vpc_cidr, 8, idx)
  ]

  public_subnets = [
    for idx, az in var.availability_zones :
    cidrsubnet(var.vpc_cidr, 8, idx + 100)
  ]

  # Environment-specific configuration
  instance_type = var.environment == "prod" ? "t3.large" : "t3.small"

  # Merge tags
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}
```

### Advanced: Workspaces, State Ops & Backend Migration

Workspaces for environment separation:

```bash
# Create and switch to workspace
terraform workspace new dev
terraform workspace select dev

# List workspaces
terraform workspace list
```

Reference the active workspace from configuration:

```hcl
resource "aws_instance" "web" {
  # ... configuration ...

  tags = {
    Environment = terraform.workspace
  }
}
```

State manipulation commands:

```bash
# Pull remote state locally
terraform state pull > terraform.tfstate.backup

# Push local state to remote
terraform state push terraform.tfstate

# Move resource to different state
terraform state mv aws_instance.web module.ec2.aws_instance.web

# Replace provider in state
terraform state replace-provider hashicorp/aws registry.terraform.io/hashicorp/aws
```

Remote backend migration:

```hcl
# Step 1: Configure new backend
terraform {
  backend "s3" {
    # new backend configuration
  }
}

# Step 2: Initialize with migration
# terraform init -migrate-state
```

### Troubleshooting

Common issues:

1. **State Lock**: Check DynamoDB/blob storage for stuck locks.
2. **Provider Version Conflicts**: Update version constraints.
3. **Circular Dependencies**: Refactor with explicit `depends_on`.
4. **Resource Drift**: Run `terraform refresh` and investigate.
5. **Large State Files**: Consider splitting into multiple states.

Debugging commands:

```bash
# Enable detailed logging
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform.log

# Refresh state from actual infrastructure
terraform refresh

# Show current state
terraform show

# List resources in state
terraform state list

# Show specific resource
terraform state show aws_instance.web

# Import existing resource
terraform import aws_instance.web i-1234567890abcdef0

# Taint resource for recreation
terraform taint aws_instance.web

# Remove resource from state
terraform state rm aws_instance.web
```

## Anti-Patterns

High-signal IaC review smells. For each: the bad pattern, why it hurts, and the corrected form.

### Hardcoded secrets or credentials

Bad: a password or access key written inline in `.tf` or `.tfvars`. Why: secrets land in Git history and state in plaintext, and rotating them means a code change. Corrected:

```hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "prod/db/password"
}

variable "db_password" {
  description = "Database admin password, injected from a secret store"
  type        = string
  sensitive   = true
}
```

### Committing state files

Bad: `terraform.tfstate` tracked in Git. Why: state contains plaintext secrets and resource metadata, and concurrent edits corrupt it. Corrected: use a remote, encrypted, locked backend and add state files to `.gitignore`.

```hcl
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "project/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### Unpinned providers or modules referenced by branch

Bad: `version = ">= 0"` or `?ref=main`. Why: applies become non-reproducible and a silent upstream change can rewrite infrastructure. Corrected: pin a version constraint and reference modules by tag.

```hcl
module "vpc" {
  source = "git::https://github.com/org/terraform-modules.git//vpc?ref=v2.1.0"
}
```

### Missing state locking or encryption

Bad: a remote backend with `encrypt = false` and no lock table. Why: two applies can race and corrupt state; an unencrypted state object leaks every secret it holds. Corrected: set `encrypt = true` and configure `dynamodb_table` (S3) or rely on native locking for other backends (see backend block above).

### Missing variable validation

Bad: a free-form `string` input with no guardrails. Why: invalid values fail deep inside the apply with a cryptic provider error. Corrected: fail fast at the interface.

```hcl
variable "environment" {
  description = "Environment name"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
```

### `count` where `for_each` belongs

Bad: `count = length(var.names)` over a list. Why: removing a middle element re-indexes every later resource, forcing needless destroy/recreate. Corrected: key by a stable identifier.

```hcl
resource "aws_iam_user" "team" {
  for_each = toset(var.usernames)
  name     = each.value
}
```

### Missing encryption at rest

Bad: an S3 bucket, RDS instance, or EBS volume created without encryption. Why: data at rest is exposed and most compliance regimes reject it. Corrected: enable provider-native encryption.

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}
```

## Worked Examples

### Unpinned module reference → version-pinned

Before:

```hcl
module "vpc" {
  source = "git::https://github.com/org/terraform-modules.git//vpc"

  name       = "production-vpc"
  cidr_block = "10.0.0.0/16"
}
```

After:

```hcl
module "vpc" {
  source = "git::https://github.com/org/terraform-modules.git//vpc?ref=v2.1.0"

  name        = "production-vpc"
  cidr_block  = "10.0.0.0/16"
  environment = var.environment
}
```

Rationale: the `before` resolves to whatever the default branch is at apply time, so the same configuration can produce different infrastructure on two runs. Pinning `?ref=v2.1.0` makes the plan reproducible and turns module upgrades into explicit, reviewable commits.

### Hardcoded secret → Secrets Manager + `sensitive`

Before:

```hcl
resource "aws_db_instance" "main" {
  identifier = "app-db"
  engine     = "postgres"
  username   = "admin"
  password   = "SuperSecret123!" # exposed in code and state
}
```

After:

```hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "prod/app-db/password"
}

resource "aws_db_instance" "main" {
  identifier = "app-db"
  engine     = "postgres"
  username   = "admin"
  password   = data.aws_secretsmanager_secret_version.db.secret_string

  storage_encrypted = true
}

output "db_endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}
```

Rationale: the literal password leaks into Git history and into state in plaintext, and rotation requires a code change. Sourcing it from Secrets Manager keeps the secret out of the repo, lets it rotate independently, and marking the output `sensitive` stops Terraform from echoing it in plan/apply logs. Adding `storage_encrypted = true` closes the encryption-at-rest gap in the same pass.

## Review Workflow

Follow these steps when reviewing a Terraform change. Verify each issue against the actual configuration before flagging it.

1. **Format and validate.** Run the cheap mechanical checks first:

   ```bash
   terraform fmt -check -recursive
   terraform init -backend=false
   terraform validate
   ```

2. **Security first.** Scan for the highest-impact problems before anything else: hardcoded secrets or credentials, overly broad IAM (`*` actions/resources), public exposure of sensitive resources, and missing encryption at rest or in transit.
3. **State configuration.** Confirm the backend is remote, encrypted (`encrypt = true`), and locked (lock table or native locking). Flag any committed state files.
4. **Module and version hygiene.** Check that Terraform and all providers are pinned, modules are referenced by tag (not branch), and module interfaces have descriptions and `validation`.
5. **Performance and structure.** Look at `for_each` vs `count`, parallelism assumptions, tagging, file organization, and `depends_on` correctness.
6. **Recommend tooling.** Where appropriate, suggest running `tfsec` or `checkov` (security), `tflint` (lint/provider rules), and `infracost` (cost impact) in CI to catch regressions automatically.
7. **Assign severity and write the report.** Apply the severity scale below, then emit the structured report. If `terraform validate` passes and the configuration is functionally correct, cap purely stylistic/structural findings at MEDIUM.

## Output Format

Produce the review as Markdown using this template:

````markdown
# Terraform Review

## Summary

<1-3 sentences: overall assessment, count of findings by severity, and whether `terraform fmt -check` / `terraform validate` pass.>

## Findings

### [CRITICAL] <short title>

- **Category:** Security | State | Versioning | Validation | Performance | Structure
- **Location:** `path/to/file.tf:line`
- **Problem:** <what is wrong>
- **Why It Matters:** <impact: exposure, cost, drift, destroy/recreate, non-reproducibility>
- **Fix:**

```hcl
# corrected configuration
```

### [HIGH] <short title>

- **Category:** ...
- **Location:** `path/to/file.tf:line`
- **Problem:** ...
- **Why It Matters:** ...
- **Fix:**

```hcl
# corrected configuration
```

## Summary Table

| Severity | Category | Location | Issue |
|----------|----------|----------|-------|
| CRITICAL | Security | `db.tf:42` | Hardcoded DB password |
| HIGH | Versioning | `versions.tf:3` | AWS provider unpinned |
| MEDIUM | Performance | `iam.tf:10` | `count` used where `for_each` fits |
| LOW | Structure | `main.tf:1` | Missing variable description |
````

## Severity Scale

Use the standardized scale, most severe first:

- **CRITICAL**: Exposed secret or credential; public exposure of a sensitive resource; state without encryption or locking; risk of a destructive change (data loss, forced replacement of stateful resources).
- **HIGH**: Missing least-privilege or encryption on an impactful resource; unpinned Terraform/provider/module versions; missing `validation` on inputs that drive impactful behavior.
- **MEDIUM**: Non-ideal structure that still works; `count` where `for_each` belongs; missing tags; weak organization.
- **LOW**: Formatting, naming, and documentation nits.

Severity cap rule (verbatim):

> If `terraform validate` passes and the configuration is functionally correct, the maximum severity for purely stylistic or structural findings is MEDIUM, not HIGH or CRITICAL.

Security findings (for example, exposed secrets) remain CRITICAL regardless of whether `terraform validate` passes.

## Quality Checklist

Before completing a review or a change, verify:

- [ ] `terraform fmt -check` and `terraform validate` were run.
- [ ] No hardcoded secrets or credentials anywhere in `.tf` / `.tfvars`.
- [ ] State is remote, locked, and encrypted; no state files are committed.
- [ ] Terraform, providers, and modules are all version-pinned (modules by tag, not branch).
- [ ] Input variables have `description` fields and `validation` where it matters.
- [ ] `for_each` is used over `count` where collection identity should be stable.
- [ ] Sensitive variables and outputs are marked `sensitive = true`.
- [ ] Encryption at rest is enabled on stateful resources (S3/RDS/EBS/etc.).
- [ ] The severity scale (including the validate-pass cap) was applied.
- [ ] Output is well-formed Markdown using the report template.

## Key References

- [Terraform Registry](https://registry.terraform.io/)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [AWS Terraform Modules](https://github.com/terraform-aws-modules)
- [Azure Terraform Modules](https://registry.terraform.io/namespaces/Azure)
- [GCP Terraform Modules](https://registry.terraform.io/namespaces/terraform-google-modules)
- [Terratest Documentation](https://terratest.gruntwork.io/)
- [TFLint Rules](https://github.com/terraform-linters/tflint)
