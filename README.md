# Commercial Auto Email Intake Service

This repository contains the Email Intake component for a Commercial Auto Insurance Submission Processing System.

The service receives broker/agent submissions through REST or a local SMTP receiver, stores case metadata in PostgreSQL, stores original attachments in S3, publishes a lightweight `CASE_CREATED` event to SQS, sends an acknowledgement email, and immediately returns the `case_id`.

It intentionally does **not** implement OCR, document understanding, document classification, extraction, underwriting analysis, rule engines, AI summaries, or LLM workflows. Those belong in a separate Documentation Service.

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
- `message_id`: optional, used for idempotency

For each request, the service:

1. Parses the inbound payload into a common email intake model.
2. Computes an idempotency key from sender, subject, message ID, and attachment hashes.
3. Returns an existing case for duplicates inside the configured window.
4. Creates a case row in `public."knight-case-table"` with status `RECEIVED`.
5. Stores each original attachment under the case S3 prefix.
6. Persists lightweight attachment metadata.
7. Publishes one `CASE_CREATED` SQS event after persistence succeeds.
8. Sends a best-effort acknowledgement email.
9. Returns `{ "case_id": "...", "status": "RECEIVED" }` immediately.

Actual file bytes are stored in local disk for local development or S3 in AWS. PostgreSQL stores metadata and relationships.

## Architecture

Local development:

```text
FastAPI/Uvicorn -> local PostgreSQL
                -> local_storage/
```

AWS deployment:

```text
Email
  |
  v
Email Intake Service
  |-- store case metadata -> RDS PostgreSQL
  |-- store attachments   -> S3
  |-- publish event       -> SQS
  `-- send acknowledgement email

SQS -> Documentation Service (future repository)
```

In the current AWS deployment:

- RDS DB instance: `knight-email-intake-db`
- RDS endpoint: `knight-email-intake-db.c3wgqma4geuk.us-east-1.rds.amazonaws.com`
- RDS database: `email_intake`
- RDS username: `email_intake_user`
- RDS security group: `sg-0feb7131c1b023d57`
- S3 bucket: `knight-email-pool`
- The database currently allows PostgreSQL access from the setup client IP only for pgAdmin testing.
- Do not commit the database password. Use shell environment variables, AWS Secrets Manager, or another secure password store.
- For production, prefer private RDS access from Lambda through the VPC.

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
    intake_service.py         Shared REST/SMTP intake workflow
    email_intake.py           Backward-compatible REST adapter
    email_parser.py           Raw email parser for SMTP intake
    smtp_receiver.py          Local SMTP receiver
    sqs_service.py            CASE_CREATED publisher
    reply_service.py          Acknowledgement email sender
  storage/
    base.py                   Storage interface
    local.py                  Local filesystem storage
    s3.py                     S3 storage
    factory.py                Selects local vs S3 backend
  utils/
    checksum.py               SHA256 checksum helper
    filenames.py              Safe upload filename helper
    logging.py                Structured JSON logging helper
  config.py                   Runtime settings from env/.env
  database.py                 SQLAlchemy engine/session setup
  lambda_handler.py           Mangum Lambda adapter
  main.py                     FastAPI app construction

migrations/
  versions/                   Alembic migrations

scripts/
  backfill_email_tables.py    Creates email_tables.xlsx for existing local submissions
  run_smtp_receiver.py        Starts the local SMTP receiver

template.yaml                 AWS SAM template
Makefile                      Local/AWS build, migration, and deployment commands
```

## Data Model

`submissions`

- `id`
- `case_id`
- `sender_email`
- `recipients`
- `subject`
- `email_body`
- `message_id`
- `received_at`
- `status`
- `attachment_count`
- `idempotency_key`

`documents`

- `id`
- `case_id`
- `submission_id`
- `original_filename`
- `source`: `email_body`, `email_tables`, or `attachment`
- `mime_type`
- `file_size`
- `s3_path`: local path in local mode, S3 URI in AWS mode
- `s3_key`: S3 object key, or local path in local mode
- `checksum`
- `status`
- `extension`
- `page_count`
- `sheet_count`
- `duplicate`
- `duplicate_of_document_id`
- `created_at`

`public."knight-case-table"`

- `case_id`: primary key UUID returned to the API caller
- `sender_email`
- `recipients`
- `subject`
- `email_body`
- `message_id`
- `idempotency_key`
- `received_at`
- `status`: initially `RECEIVED`
- `attachment_count`
- `s3_location`: folder/prefix containing original attachments
- `report_location`: reserved for future use

## Storage Behavior

Local mode:

```text
local_storage/cases/{case_id}/original/{filename}
```

AWS mode:

```text
s3://{S3_BUCKET}/cases/{case_id}/original/{filename}
```

Each case stores:

- `email_body.html`: preserved email body content
- `email_tables.xlsx`: generated when the email body contains parseable tables
- original submitted attachments

Email body content and generated table files are never included in the SQS event; the Documentation Service can retrieve them later by `case_id`.

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
SQS_QUEUE_URL=
SMTP_HOST=127.0.0.1
SMTP_PORT=8025
SMTP_REPLY_FROM=submissions@knight.local
SMTP_REPLY_ENABLED=false
DUPLICATE_WINDOW_MINUTES=60
LOG_LEVEL=INFO
```

Create the local database, run migrations, and start the API:

```bash
createdb email_intake
alembic upgrade head
uvicorn app.main:app --reload
```

Start the local SMTP receiver in another terminal:

```bash
python scripts/run_smtp_receiver.py
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

Successful REST responses are intentionally small:

```json
{
  "case_id": "26ddf106-c7bb-440c-9299-ff7d73c4eb81",
  "status": "RECEIVED"
}
```

AWS endpoint version:

```bash
curl -X POST "https://bftq0ig423.execute-api.us-east-1.amazonaws.com/prod/ingest-email" \
  -F "sender_email=broker@example.com" \
  -F "subject=New commercial auto submission" \
  -F "email_body=<table><tr><th>Year</th><th>Units</th></tr><tr><td>2026</td><td>20</td></tr></table>" \
  -F "attachments=@./examples/acord.pdf;type=application/pdf"
```

SMTP testing example:

```bash
python - <<'PY'
import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg["From"] = "broker@example.com"
msg["To"] = "submissions@knight.local"
msg["Subject"] = "New commercial auto submission"
msg["Message-ID"] = "<submission-001@example.com>"
msg.set_content("Please process this submission.")
msg.add_attachment(b"sample", maintype="application", subtype="pdf", filename="loss_runs.pdf")

with smtplib.SMTP("127.0.0.1", 8025) as smtp:
    smtp.send_message(msg)
PY
```

See also:

- [examples/ingest-email-request.md](examples/ingest-email-request.md)
- [examples/ingest-email-response.json](examples/ingest-email-response.json)

## SQS Event

After database persistence and attachment upload succeed, the service publishes one lightweight message:

```json
{
  "event_type": "CASE_CREATED",
  "case_id": "26ddf106-c7bb-440c-9299-ff7d73c4eb81",
  "received_at": "2026-06-25T12:00:00+00:00",
  "attachment_count": 3
}
```

The message never includes attachment bytes, email body content, extracted text, or document understanding output.

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
  SQS_QUEUE_URL="$SQS_QUEUE_URL" \
  AWS_REGION="us-east-1" \
  VPC_SUBNET_IDS="subnet-0855e9dcfa421ccaa,subnet-0ab8e46cd1a51c872,subnet-007d3b027d3de5dba,subnet-0c3d9a488e1e7a434,subnet-0c52f758e363969d0,subnet-03d4be6e11443a4d9" \
  VPC_SECURITY_GROUP_IDS="sg-0c4d439f509ca127b"
```

For local development:

```bash
make dev
```

Do not commit real database credentials. Use shell environment variables or a secrets manager.

Current AWS RDS connection shape:

```text
postgresql+psycopg://email_intake_user:<password>@knight-email-intake-db.c3wgqma4geuk.us-east-1.rds.amazonaws.com:5432/email_intake?sslmode=require
```

For pgAdmin 4:

```text
Host: knight-email-intake-db.c3wgqma4geuk.us-east-1.rds.amazonaws.com
Port: 5432
Database: email_intake
Username: email_intake_user
```

The AWS database has these public schema tables:

```text
alembic_version
documents
knight-case-table
submissions
```

The case table stores the generated case ID and S3 locations:

```sql
SELECT case_id, s3_location, report_location
FROM public."knight-case-table";
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

The response reports API, database, S3/storage, and SQS connectivity.

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

- REST accepts one email submission per request.
- Local SMTP intake is intended for development and integration testing.
- Duplicate detection uses sender, subject, message ID, and attachment hashes inside `DUPLICATE_WINDOW_MINUTES`.
- No OCR, document understanding, document classification, underwriting analysis, rule engine, AI summary, or LLM workflow is implemented in this service.
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

Check S3 output for a case:

```bash
aws s3 ls s3://knight-email-pool/cases/{case_id}/original/ \
  --region us-east-1
```
