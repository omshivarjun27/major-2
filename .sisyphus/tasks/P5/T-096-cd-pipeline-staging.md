# T-096: CD Pipeline Staging

## Metadata
- **Phase**: P5
- **Cluster**: CL-OPS
- **Risk Tier**: Medium
- **Upstream Deps**: []
- **Downstream Impact**: [T-097, T-109]
- **Current State**: completed

## Objective

Implement a CD pipeline for automated deployment to staging. Extend `.github/workflows/` with a `deploy-staging.yml` workflow triggered on main branch pushes. Pipeline stages: build Docker image, push to registry, deploy to staging, run smoke tests, notify. Use GitHub Actions with environment-specific secrets. Implement blue-green deployment strategy with instant rollback capability. Staging environment mirrors production configuration.

## Acceptance Criteria

1. ✅ deploy-staging.yml workflow triggered on main push
2. ✅ Docker image build with buildx and caching
3. ✅ Push to GitHub Container Registry (ghcr.io)
4. ✅ Staging deployment job with environment secrets
5. ✅ Smoke tests against staging
6. ✅ Notification job (Slack webhook support)
7. ✅ Automatic rollback on smoke test failure
8. ✅ Manual trigger option (workflow_dispatch)
9. ✅ SBOM generation for security auditing

## Implementation Notes

Created `.github/workflows/deploy-staging.yml` with:
- **Build job**: Docker buildx, multi-platform support, GHA caching, SBOM generation
- **Deploy job**: SSH-based deployment (configurable), health check wait
- **Smoke tests**: HTTP health and metrics endpoint validation
- **Notify job**: GitHub summary + Slack webhook notification
- **Rollback job**: Automatic on smoke test failure

Environment secrets required:
- `STAGING_HOST`: Staging server hostname
- `STAGING_USER`: SSH user for deployment
- `STAGING_SSH_KEY`: SSH private key
- `STAGING_URL`: Public staging URL for smoke tests
- `SLACK_WEBHOOK_URL`: (Optional) Slack notifications

## Test Requirements

- Integration: Workflow syntax validation via act or GitHub
- Manual: Trigger workflow_dispatch to verify end-to-end
