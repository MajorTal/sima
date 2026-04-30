#!/usr/bin/env bash
# Pause Sima AWS resources to stop ongoing compute charges.
#
# Scales all ECS Fargate services to 0 and disables EventBridge schedules.
# Fully reversible via scripts/aws_resume.sh. No data loss: RDS, S3, SQS,
# Secrets Manager, ECR, ALB, NAT Gateway, and Route53 records are left intact.
#
# What this stops paying for:
#   - 4x Fargate tasks (web, api, ingest-api, brain) running 24/7
#   - Scheduled Fargate task launches (minute tick, autonomous tick, sleep)
#
# What this does NOT pause (still incurring cost):
#   - RDS db.t4g.micro instance (~$12-15/mo) — stop manually if needed:
#       aws rds stop-db-instance --db-instance-identifier sima-sima
#       (AWS auto-restarts after 7 days)
#   - NAT Gateway (~$32/mo) — requires `terraform destroy -target=module.vpc` to remove
#   - ALB (~$16/mo) — requires `terraform destroy -target=module.alb` to remove
#   - Secrets Manager (~$0.40/secret/mo)

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-private}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENV="sima"
CLUSTER="sima-${ENV}"

AWS=(aws --profile "$AWS_PROFILE" --region "$AWS_REGION")

SERVICES=(
  "sima-${ENV}-web"
  "sima-${ENV}-api"
  "sima-${ENV}-ingest-api"
  "sima-${ENV}-brain"
)

EVENT_RULES=(
  "sima-${ENV}-minute-tick"
  "sima-${ENV}-autonomous-tick"
  "sima-${ENV}-sleep-schedule"
)

echo "==> Pausing Sima on AWS (profile=$AWS_PROFILE region=$AWS_REGION)"
echo

echo "==> Disabling EventBridge rules"
for rule in "${EVENT_RULES[@]}"; do
  if "${AWS[@]}" events describe-rule --name "$rule" >/dev/null 2>&1; then
    "${AWS[@]}" events disable-rule --name "$rule"
    echo "    [disabled]  $rule"
  else
    echo "    [skipped]   $rule (not found)"
  fi
done
echo

echo "==> Scaling ECS services to desired_count=0"
for svc in "${SERVICES[@]}"; do
  if "${AWS[@]}" ecs describe-services --cluster "$CLUSTER" --services "$svc" \
      --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
    "${AWS[@]}" ecs update-service \
      --cluster "$CLUSTER" \
      --service "$svc" \
      --desired-count 0 >/dev/null
    echo "    [scaled=0]  $svc"
  else
    echo "    [skipped]   $svc (not active)"
  fi
done
echo

echo "==> Stopping any currently running tasks (faster billing stop)"
running_tasks=$("${AWS[@]}" ecs list-tasks --cluster "$CLUSTER" \
  --desired-status RUNNING --query 'taskArns[]' --output text 2>/dev/null || true)
if [[ -n "${running_tasks// /}" && "$running_tasks" != "None" ]]; then
  for arn in $running_tasks; do
    "${AWS[@]}" ecs stop-task --cluster "$CLUSTER" --task "$arn" \
      --reason "paused via aws_pause.sh" >/dev/null
    echo "    [stopped]   $arn"
  done
else
  echo "    (no running tasks)"
fi
echo

echo "==> Done. Run scripts/aws_resume.sh to bring Sima back."
echo "    Note: RDS, NAT Gateway, and ALB still incur cost. See script header."
