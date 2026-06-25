# Commercial Auto Email Intake Service

This repository contains the Email Intake component for a Commercial Auto Insurance Submission Processing System.

The service receives one simulated broker/agent email submission per API request, stores the submission metadata in PostgreSQL, stores files locally or in S3, creates document inventory records, detects duplicate attachments within the same submission, and preserves email-body tables as Excel workbooks.

It intentionally does **not** implement OCR, document classification, document extraction, underwriting analysis, or AI recommendations yet.

## Current AWS Endpoint

The service is deployed through API Gateway and Lambda:

```text
https://bftq0ig423.execute-api.us-east-1.amazonaws.com/prod/
```

API docs:

```text
https://bftq0ig423.execute-api.us-east-1.amazonaws.com/prod/docs
https://bftq0ig423.execute-api.us-east-1.amazonaws.com/prod/openapi.json
https://bftq0ig423.execute-api.us-east-1.amazonaws.com/prod/redoc
```

## What It Does

`POST /ingest-email` accepts multipart form data:

- `sender_email`
- `subject`
- `email_body`
- `attachments`: one or more uploaded files

For each request, the service:

1. Creates a `Submission` row.
2. Stores the email body as `email_body.html`.
3. Parses tables from the email body and stores them as `email_tables.xlsx` when tables are found.
4. Stores each uploaded attachment.
5. Computes SHA256 checksums.
6. Detects duplicate uploaded attachments within the same submission.
7. Stores document inventory metadata.
8. Returns a submission summary.

Actual file bytes are stored in local disk for local development or S3 in AWS. PostgreSQL stores metadata and relationships.

## Architecture

Local development:

```text
FastAPI/Uvicorn -> local PostgreSQL
                -> local_storage/
```

AWS deployment:

```text
API Gateway -> Lambda/FastAPI -> RDS PostgreSQL
                            -> S3
```

In the current AWS deployment:

- RDS database: `knight_email_intake`
- S3 bucket: `knight-email-pool`
- Lambda runs inside the RDS VPC.
- An S3 Gateway VPC endpoint allows the VPC Lambda to write to S3.

## Code Structure

```text
app/
  api/
    routes.py                 FastAPI route definitions
  models/
    submission.py             SQLAlchemy Submission model
    document.py               SQLAlchemy Document model
  repositories/
    submission_repository.py  Database write helpers
  schemas/
    email.py                  Pydantic request/response schemas
  services/
    email_intake.py           Main intake workflow orchestration
  storage/
    base.py                   Storage interface
    local.py                  Local filesystem storage
    s3.py                     S3 storage
    factory.py                Selects local vs S3 backend
  utils/
    checksum.py               SHA256 checksum helper
    duplicates.py             Duplicate lookup helper
    email_body.py             Email body HTML preservation
    email_tables.py           HTML/text table to XLSX conversion
    filenames.py              Safe upload filename helper
    inventory.py              PDF page count and Excel sheet count
  config.py                   Runtime settings from env/.env
  database.py                 SQLAlchemy engine/session setup
  lambda_handler.py           Mangum Lambda adapter
  main.py                     FastAPI app construction

migrations/
  versions/                   Alembic migrations

scripts/
  backfill_email_tables.py    Creates email_tables.xlsx for existing local submissions

template.yaml                 AWS SAM template
Makefile                      Local/AWS build, migration, and deployment commands
```

## Data Model

`submissions`

- `id`
- `sender_email`
- `subject`
- `email_body`
- `received_at`
- `status`

`documents`

- `id`
- `submission_id`
- `original_filename`
- `source`: `email_body`, `email_tables`, or `attachment`
- `mime_type`
- `file_size`
- `s3_path`: local path in local mode, S3 URI in AWS mode
- `checksum`
- `status`
- `extension`
- `page_count`
- `sheet_count`
- `duplicate`
- `duplicate_of_document_id`
- `created_at`

## Storage Behavior

Local mode:

```text
local_storage/submissions/{submission_id}/attachments/{filename}
```

AWS mode:

```text
s3://{S3_BUCKET}/submissions/{submission_id}/attachments/{filename}
```

The response field is still named `s3_path` for API compatibility. In local mode, it contains a local file path.

## Email Body And Tables

The original email body is always stored as a document:

```text
email_body.html
source = email_body
```

If `email_body` already contains HTML, it is stored unchanged so table formatting is preserved. If the body is plain text, it is wrapped in simple HTML.

When tables are detected, the service also creates:

```text
email_tables.xlsx
source = email_tables
```

Each parsed table becomes a separate workbook sheet. The parser supports real HTML `<table>` elements and a pragmatic parser for known pasted text-table sections such as historical values, summary totals, and auto liability losses.

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Default local `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/email_intake
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=local_storage
ROOT_PATH=
S3_BUCKET=email-intake-submissions
AWS_REGION=us-east-1
```

Create the local database, run migrations, and start the API:

```bash
createdb email_intake
alembic upgrade head
uvicorn app.main:app --reload
```

Local docs:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

## Example Request

```bash
curl -X POST http://127.0.0.1:8000/ingest-email \
  -F "sender_email=broker@example.com" \
  -F "subject=New commercial auto submission" \
  -F "email_body=<table><tr><th>Year</th><th>Units</th></tr><tr><td>2026</td><td>20</td></tr></table>" \
  -F "attachments=@./examples/acord.pdf;type=application/pdf"
```

AWS endpoint version:

```bash
curl -X POST "https://bftq0ig423.execute-api.us-east-1.amazonaws.com/prod/ingest-email" \
  -F "sender_email=broker@example.com" \
  -F "subject=New commercial auto submission" \
  -F "email_body=<table><tr><th>Year</th><th>Units</th></tr><tr><td>2026</td><td>20</td></tr></table>" \
  -F "attachments=@./examples/acord.pdf;type=application/pdf"
```

See also:

- [examples/ingest-email-request.md](examples/ingest-email-request.md)
- [examples/ingest-email-response.json](examples/ingest-email-response.json)

## AWS Deployment

The Lambda entry point is:

```text
app.lambda_handler.handler
```

The AWS SAM template is:

```text
template.yaml
```

Detailed deployment notes are in:

```text
docs/aws-lambda-deploy.md
```

Common deployment commands:

```bash
make aws-deploy-private \
  DATABASE_URL="$DATABASE_URL" \
  S3_BUCKET="knight-email-pool" \
  AWS_REGION="us-east-1" \
  VPC_SUBNET_IDS="subnet-0855e9dcfa421ccaa,subnet-0ab8e46cd1a51c872,subnet-007d3b027d3de5dba,subnet-0c3d9a488e1e7a434,subnet-0c52f758e363969d0,subnet-03d4be6e11443a4d9" \
  VPC_SECURITY_GROUP_IDS="sg-0c4d439f509ca127b"
```

For local development:

```bash
make dev
```

Do not commit real database credentials. Use shell environment variables or a secrets manager.

## AWS Networking Notes

The deployed Lambda must reach both RDS and S3.

Current working setup:

- Lambda is attached to the same VPC as RDS.
- Lambda uses a security group that can connect to RDS on port `5432`.
- The VPC has an S3 Gateway VPC endpoint attached to the route table.

Without the S3 VPC endpoint or NAT, S3 uploads from Lambda will hang and API Gateway may return `504`.

The RDS public `0.0.0.0/0` test rule should be removed after debugging. Lambda no longer needs it when using VPC security-group based access.

## Migrations

Alembic migrations live in `migrations/versions`.

Run locally:

```bash
alembic upgrade head
```

Run against RDS:

```bash
make migrate DATABASE_URL="$DATABASE_URL"
```

`migrations/env.py` escapes `%` characters for Alembic config handling, which matters because URL-encoded passwords may contain values like `%21`.

## Existing Limitations

- One email per request.
- Multiple attachments per email are supported.
- Duplicate detection is scoped to uploaded attachments in the same submission.
- No OCR yet.
- No document type classification yet.
- No underwriting analysis yet.
- No AI recommendations yet.
- API Gateway payload limits still apply. Large packages should eventually use presigned S3 uploads plus an ingestion request containing S3 object references.

## Useful Operational Checks

Check deployed stack resources:

```bash
aws cloudformation describe-stack-resources \
  --stack-name knight-email-intake-service \
  --region us-east-1
```

Tail Lambda logs:

```bash
aws logs tail /aws/lambda/knight-email-intake-service-EmailIntakeFunction-Ec70vy5tk4Vq \
  --region us-east-1 \
  --since 10m \
  --format short
```

Check S3 output for a submission:

```bash
aws s3 ls s3://knight-email-pool/submissions/{submission_id}/attachments/ \
  --region us-east-1
```
