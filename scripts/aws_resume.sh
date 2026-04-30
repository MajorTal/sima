#!/usr/bin/env bash
# Resume Sima AWS resources after running scripts/aws_pause.sh.
#
# Re-enables EventBridge schedules and scales ECS services back to their
# normal desired_count (1 each, matching the Terraform config).
#
# If you stopped RDS manually, start it back with:
#   aws rds start-db-instance --db-instance-identifier sima-sima

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-private}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENV="sima"
CLUSTER="sima-${ENV}"

AWS=(aws --profile "$AWS_PROFILE" --region "$AWS_REGION")

# service_name:desired_count (matches infra/terraform/envs/sima/main.tf)
SERVICES=(
  "sima-${ENV}-web:1"
  "sima-${ENV}-api:1"
  "sima-${ENV}-ingest-api:1"
  "sima-${ENV}-brain:1"
)

EVENT_RULES=(
  "sima-${ENV}-minute-tick"
  "sima-${ENV}-autonomous-tick"
  "sima-${ENV}-sleep-schedule"
)

echo "==> Resuming Sima on AWS (profile=$AWS_PROFILE region=$AWS_REGION)"
echo

echo "==> Scaling ECS services back up"
for entry in "${SERVICES[@]}"; do
  svc="${entry%%:*}"
  count="${entry##*:}"
  if "${AWS[@]}" ecs describe-services --cluster "$CLUSTER" --services "$svc" \
      --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
    "${AWS[@]}" ecs update-service \
      --cluster "$CLUSTER" \
      --service "$svc" \
      --desired-count "$count" >/dev/null
    echo "    [scaled=$count]  $svc"
  else
    echo "    [skipped]    $svc (not active)"
  fi
done
echo

echo "==> Re-enabling EventBridge rules"
for rule in "${EVENT_RULES[@]}"; do
  if "${AWS[@]}" events describe-rule --name "$rule" >/dev/null 2>&1; then
    "${AWS[@]}" events enable-rule --name "$rule"
    echo "    [enabled]   $rule"
  else
    echo "    [skipped]   $rule (not found)"
  fi
done
echo

echo "==> Done. Tasks will take ~1-2 minutes to reach RUNNING."
