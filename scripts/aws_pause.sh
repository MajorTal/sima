#!/usr/bin/env bash
# Pause Sima AWS resources to stop ongoing compute charges.
#
# Default: scales all ECS Fargate services to 0 and disables EventBridge
# schedules. Fully reversible via scripts/aws_resume.sh. No data loss.
#
# --deep: ALSO destroys RDS and the NAT Gateway via `terraform destroy
# -target=...`. RDS data is wiped (final snapshot is skipped). The private
# route table is cascade-destroyed because it references the NAT Gateway;
# `terraform apply` on resume recreates RDS, NAT, EIP, and the routes from
# scratch. Use --deep only when there is no valuable data in RDS.
#
# Cost stopped (default mode):
#   - 4x Fargate tasks (web, api, ingest-api, brain)
#   - Scheduled Fargate task launches (minute, autonomous, sleep)
#
# Cost stopped (--deep, additional):
#   - NAT Gateway + Elastic IP (~$32/mo + data)
#   - RDS db.t4g.micro + gp3 storage (~$12-15/mo)
#
# Still incurring cost in either mode:
#   - ALB (~$16/mo)
#   - Secrets Manager (~$0.40/secret/mo)
#   - Route53 hosted zone (~$0.50/mo)
#   - S3 / ECR storage (usually pennies)

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

echo "==> Pausing Sima on AWS (profile=$AWS_PROFILE region=$AWS_REGION, deep=$DEEP)"
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

if [[ "$DEEP" -eq 1 ]]; then
  TF_DIR="$(git rev-parse --show-toplevel)/infra/terraform/envs/sima"
  echo "==> DEEP pause: destroying RDS and NAT Gateway via Terraform"
  echo "    working dir: $TF_DIR"
  echo "    WARNING: this WIPES the RDS instance (no final snapshot)."
  read -r -p "    Type 'destroy' to continue: " confirm
  if [[ "$confirm" != "destroy" ]]; then
    echo "    aborted."
    exit 1
  fi

  cd "$TF_DIR"

  AWS_PROFILE="$AWS_PROFILE" terraform init -input=false

  # The RDS instance has skip_final_snapshot configured per the module;
  # if not, this command will fail and you'll need to set it.
  AWS_PROFILE="$AWS_PROFILE" terraform destroy -auto-approve \
    -target=module.rds \
    -target=module.vpc.aws_nat_gateway.main \
    -target=module.vpc.aws_eip.nat

  echo
  echo "    [destroyed] module.rds"
  echo "    [destroyed] module.vpc.aws_nat_gateway.main"
  echo "    [destroyed] module.vpc.aws_eip.nat"
  echo "    (private route table is cascade-destroyed; apply will recreate.)"
fi

echo
echo "==> Done. Run scripts/aws_resume.sh to bring Sima back."
if [[ "$DEEP" -eq 1 ]]; then
  echo "    Resume must use: scripts/aws_resume.sh --deep"
  echo "    (it runs 'terraform apply' to recreate RDS/NAT, then scales ECS up.)"
fi
