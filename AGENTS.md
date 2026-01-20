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

## Deployment

### Prerequisites

1. AWS SSO login: `aws sso login --profile private`
2. Docker running locally
3. Terraform installed

### Full Deployment Process

1. **Apply Terraform changes** (updates secrets, ECS task definitions, ALB rules):
   ```bash
   cd infra/terraform/envs/sima
   terraform init
   terraform apply
   ```

2. **Login to ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 --profile private | \
     docker login --username AWS --password-stdin 322989427387.dkr.ecr.us-east-1.amazonaws.com
   ```

3. **Build Docker images** (from repo root):
   ```bash
   # API service
   docker build -t 322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/api:latest \
     -f services/api/Dockerfile .

   # Web frontend
   cd services/web
   docker build -t 322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/web:latest .
   ```

4. **Push to ECR**:
   ```bash
   docker push 322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/api:latest
   docker push 322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/web:latest
   ```

5. **Force ECS service deployment**:
   ```bash
   aws ecs update-service --cluster sima-sima --service sima-sima-api \
     --force-new-deployment --profile private --region us-east-1

   aws ecs update-service --cluster sima-sima --service sima-sima-web \
     --force-new-deployment --profile private --region us-east-1
   ```

6. **Wait for deployment to stabilize**:
   ```bash
   aws ecs wait services-stable --cluster sima-sima \
     --services sima-sima-api sima-sima-web --profile private --region us-east-1
   ```

### ECR Repository URLs

| Service | ECR URL |
|---------|---------|
| api | `322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/api` |
| web | `322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/web` |
| orchestrator | `322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/orchestrator` |
| ingest-api | `322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/ingest-api` |
| sleep | `322989427387.dkr.ecr.us-east-1.amazonaws.com/sima-sima/sleep` |

## Debugging

### Check ECS Service Status

```bash
# List services and their status
aws ecs describe-services --cluster sima-sima \
  --services sima-sima-api sima-sima-web sima-sima-orchestrator \
  --profile private --region us-east-1 \
  --query 'services[*].[serviceName,runningCount,desiredCount,deployments[0].rolloutState]' \
  --output table
```

### View ECS Logs

```bash
# View recent API logs
aws logs tail /ecs/sima-sima --profile private --region us-east-1 \
  --filter-pattern "api" --follow

# View specific service logs
aws logs filter-log-events --log-group-name /ecs/sima-sima \
  --log-stream-name-prefix "api" --profile private --region us-east-1 \
  --limit 50 --query 'events[*].message' --output text
```

### Check ALB Routing Rules

The ALB routes requests based on path patterns:
- `/traces`, `/events`, `/memories`, `/metrics`, `/admin/*`, `/auth/*`, `/ws/*`, `/health` → API target group
- `/ingest/*`, `/webhook/*` → Ingest API target group
- Everything else (including `/admin` page) → Web target group (default)

```bash
# List all ALB listener rules
aws elbv2 describe-rules \
  --listener-arn "arn:aws:elasticloadbalancing:us-east-1:322989427387:listener/app/sima-sima/cc0fb7afd52b67a2/4167d2abe8f53ab2" \
  --profile private --region us-east-1 --output json | \
  jq '.Rules[] | {Priority, Paths: .Conditions[0].PathPatternConfig.Values}'
```

**Important**: Frontend pages (like `/admin`) must NOT be in the API path rules, or they'll return JSON errors instead of HTML.

### Test Endpoints

```bash
# Test API health
curl -s https://sima.talsai.com/health

# Test frontend page (should return HTML)
curl -s -I https://sima.talsai.com/admin | head -5

# Test API endpoint (should return JSON)
curl -s https://sima.talsai.com/admin/status
```

### Common Issues

1. **"Not Found" JSON on frontend pages**: The ALB is routing the page to the API instead of the web frontend. Check that the path is NOT in any API listener rules.

2. **Deployment stuck**: Check ECS events for the service:
   ```bash
   aws ecs describe-services --cluster sima-sima --services sima-sima-api \
     --profile private --region us-east-1 --query 'services[0].events[:5]'
   ```

3. **Container failing to start**: Check CloudWatch logs and ensure all required environment variables/secrets are configured in the ECS task definition.
