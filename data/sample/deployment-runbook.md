# Deployment Runbook

## Standard deployment

All production deployments go through the CI/CD pipeline. Merging to `main` automatically
deploys to the `dev` environment. Production deployment requires pushing a semantic version tag
(for example `v1.2.0`), which triggers the release workflow and requires a manual approval from
a team lead in GitHub Environments before it proceeds.

## Rollback procedure

If a deployment introduces a regression, roll back by redeploying the previous known-good image
digest rather than reverting and rebuilding. Every release is tagged with an immutable digest, so
rollback is a redeploy action, not a new build. A rollback should be verified with the smoke test
script before being considered complete.

## Zero-downtime deploys

Deployments use rolling updates. The readiness probe (`/ready`) determines when a new instance
starts receiving traffic; the previous instance is only removed once the replacement passes
readiness. If a new instance never becomes ready, the deployment stalls safely rather than taking
the service down.

## Pre-deployment checklist

Before deploying to production: confirm CI is green on the target commit, confirm the security
scan has no unresolved critical findings, and confirm a rollback target (the current production
image digest) has been noted somewhere accessible to the on-call engineer.
