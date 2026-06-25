# Example API Request

```bash
curl -X POST http://localhost:8000/ingest-email \
  -F "sender_email=broker@example.com" \
  -F "subject=New commercial auto submission - ACME Logistics" \
  -F "email_body=Please process the attached application package." \
  -F "attachments=@./examples/acord.pdf;type=application/pdf" \
  -F "attachments=@./examples/loss-runs.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  -F "attachments=@./examples/driver-license.jpg;type=image/jpeg"
```
