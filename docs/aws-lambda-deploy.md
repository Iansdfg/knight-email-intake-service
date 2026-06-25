# Deploy To API Gateway And Lambda

This deployment runs:

```text
API Gateway -> Lambda FastAPI app -> RDS PostgreSQL
                                  -> S3 files
```

RDS stores submission and document metadata. S3 stores file bytes, including uploaded attachments, `email_body.html`, and generated `email_tables.xlsx`.

## Prerequisites

- AWS SAM CLI
- Docker, recommended for `sam build --use-container`
- An S3 bucket for intake files
- An RDS PostgreSQL database
- A Lambda security group that can connect to RDS on TCP `5432`
- Private subnet IDs if the RDS instance is private

## Environment Values

Use an RDS URL like:

```text
postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require
```

## Run Migrations Against RDS

Run migrations once from a machine that can reach RDS:

```bash
export DATABASE_URL="postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require"
alembic upgrade head
```

Do not run migrations inside every Lambda invocation.

## Build

Use the container build so compiled dependencies are built for Lambda Linux:

```bash
make build
```

The `.aws-samignore` file excludes local test uploads and virtualenv files from the Lambda package.

## Makefile Deploy Flow

Run migrations once against RDS:

```bash
make migrate \
  DATABASE_URL='postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require'
```

Build:

```bash
make build
```

Deploy to private RDS:

```bash
make deploy-private \
  DATABASE_URL='postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require' \
  S3_BUCKET='email-intake-submissions' \
  AWS_REGION='us-east-1' \
  VPC_SUBNET_IDS='subnet-abc123,subnet-def456' \
  VPC_SECURITY_GROUP_IDS='sg-abc123'
```

For temporary public RDS development:

```bash
make deploy-public \
  DATABASE_URL='postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require' \
  S3_BUCKET='email-intake-submissions' \
  AWS_REGION='us-east-1'
```

## Deploy

For private RDS:

```bash
sam deploy --guided \
  --parameter-overrides \
    DatabaseUrl='postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require' \
    S3Bucket='email-intake-submissions' \
    VpcSubnetIds='subnet-abc123,subnet-def456' \
    VpcSecurityGroupIds='sg-abc123'
```

For a temporary public RDS development database, omit the VPC parameters:

```bash
sam deploy --guided \
  --parameter-overrides \
    DatabaseUrl='postgresql+psycopg://email_intake_user:PASSWORD@your-rds-endpoint.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require' \
    S3Bucket='email-intake-submissions'
```

## Test

After deploy, SAM prints `ApiUrl`. Test with:

```bash
curl -X POST 'https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/ingest-email' \
  -F 'sender_email=broker@example.com' \
  -F 'subject=New commercial auto submission - ACME Logistics' \
  -F 'email_body=<table><tr><th>Year</th><th>Units</th></tr><tr><td>2026</td><td>20</td></tr></table>' \
  -F 'attachments=@./examples/acord.pdf;type=application/pdf'
```

## Production Notes

- Prefer RDS Proxy for production Lambda database connections.
- Keep RDS private in a VPC.
- For large submission packages, use presigned S3 uploads and pass S3 object references to a future ingestion endpoint. API Gateway has payload limits.
- Store `DATABASE_URL` in AWS Secrets Manager for production; the SAM parameter is enough for first deployment testing.
