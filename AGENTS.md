# AGENTS.md

Instructions for AI agents working on this codebase.

## AWS Authentication

Always use the private AWS profile:

```bash
export AWS_PROFILE=private
aws sso login
```

## Secrets Management

**Always use AWS CLI to manage secrets.** Never use Terraform for secrets.

### Adding a secret to AWS Secrets Manager

```bash
AWS_PROFILE=private aws secretsmanager create-secret \
  --name "sima/<service>/<secret-name>" \
  --secret-string "<secret-value>" \
  --description "<description>" \
  --region us-east-1
```

### Updating an existing secret

```bash
AWS_PROFILE=private aws secretsmanager put-secret-value \
  --secret-id "sima/<service>/<secret-name>" \
  --secret-string "<new-value>" \
  --region us-east-1
```

### Current secrets

| Secret Name | Description |
|-------------|-------------|
| `sima/telegram/bot-token` | Telegram bot token for synthc_bot |

### Local development

For local development, secrets go in `.env` file (not committed to git).
