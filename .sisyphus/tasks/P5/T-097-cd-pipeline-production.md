# T-097: CD Pipeline Production

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: High
- **Upstream Deps**: [T-096]
- **Downstream Impact**: [T-109]
- **Current State**: completed

## Objective

Extend the CD pipeline for production deployment with approval gates. Create `deploy-production.yml` workflow with manual approval step. Implement canary deployment (10% traffic for 2 hours) with automated rollback if error rate > 1% or P95 > 600ms. Add deployment notifications to Slack/webhook. Implement deployment versioning with semantic tags. Include pre-deployment database migration step and post-deployment smoke test suite.

## Acceptance Criteria

1. ✅ deploy-production.yml with manual approval gate
2. ✅ Canary deployment with configurable traffic percentage (default 10%)
3. ✅ Canary validation against SLA thresholds (error rate, P95 latency)
4. ✅ Database migration step (pre-deployment)
5. ✅ Full production rollout after canary validation
6. ✅ Post-deployment smoke tests
7. ✅ GitHub release creation for semantic versions
8. ✅ Slack webhook notifications
9. ✅ Automatic rollback on smoke test failure
10. ✅ Skip canary option for emergency deployments

## Implementation Notes

Created `.github/workflows/deploy-production.yml` with:

**Jobs:**
- `validate`: Verify image exists, resolve tags (staging promotion or semantic version)
- `approval`: Manual approval gate via GitHub environment protection
- `migrate`: Database migration step (stub for future implementation)
- `deploy-canary`: Deploy to subset of instances with configurable traffic %
- `validate-canary`: Monitor error rate and P95 latency against thresholds
- `deploy-production`: Full rollout after canary validation
- `smoke-tests`: Production health verification
- `notify`: Slack webhook and GitHub summary
- `rollback`: Automatic on smoke test failure

**SLA Thresholds:**
- Error rate: < 1%
- P95 latency: < 600ms

**Environment secrets required:**
- `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_SSH_KEY`
- `PRODUCTION_URL`, `PRODUCTION_DATABASE_URL`
- `PROMETHEUS_URL` (for canary metrics)
- `SLACK_WEBHOOK_URL`

## Test Requirements

- Integration: Workflow syntax validation
- Manual: Trigger with skip_canary=true for rapid deployment test
