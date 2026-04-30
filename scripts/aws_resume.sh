#!/usr/bin/env bash
# Resume Sima AWS resources after running scripts/aws_pause.sh.
#
# Default: re-enables EventBridge schedules and scales ECS services back to
# their normal desired_count (1 each, matching the Terraform config).
#
# --deep: first runs `terraform apply` to recreate RDS and the NAT Gateway
# (and the cascade-destroyed private route table), then scales ECS up.
# Use this if you ran `aws_pause.sh --deep`.
#
# Manual RDS stop (non-deep) restart: aws rds start-db-instance --db-instance-identifier sima-sima

set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-private}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENV="sima"
CLUSTER="sima-${ENV}"

DEEP=0
for arg in "$@"; do
  case "$arg" in
    --deep) DEEP=1 ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

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

echo "==> Resuming Sima on AWS (profile=$AWS_PROFILE region=$AWS_REGION, deep=$DEEP)"
echo

if [[ "$DEEP" -eq 1 ]]; then
  TF_DIR="$(git rev-parse --show-toplevel)/infra/terraform/envs/sima"
  echo "==> DEEP resume: recreating RDS and NAT Gateway via Terraform"
  echo "    working dir: $TF_DIR"
  cd "$TF_DIR"
  AWS_PROFILE="$AWS_PROFILE" terraform apply -auto-approve
  cd - >/dev/null
  echo
fi

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
if [[ "$DEEP" -eq 1 ]]; then
  echo "    Run DB migrations against the fresh RDS:"
  echo "      cd packages/sima-storage && uv run alembic upgrade head"
fi
