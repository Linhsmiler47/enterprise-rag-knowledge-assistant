# Engineering Onboarding Guide

## First day setup

New engineers should request access to the version control system, the cloud provider console
(read-only initially), and the team chat workspace before their first day, so accounts are ready
when they arrive. On the first day, a buddy is assigned to walk through the codebase structure
and the local development setup.

## Local development environment

Every project in this organization follows the same local development pattern: clone the
repository, run the setup command, copy the example environment file, and start the local stack.
If `make dev` (or the project's equivalent) does not work within the first hour of following the
project's own local-development documentation, that is treated as a bug in the documentation and
should be reported, not silently worked around.

## First contribution

New engineers are expected to make a small, low-risk first contribution within their first week
-- typically a documentation fix or a small test addition -- specifically to exercise the full
pull request and CI pipeline before attempting anything larger.

## Who to ask

For local environment issues, ask your assigned buddy first. For access/permissions issues,
contact the platform team. For anything related to production systems, do not experiment
directly in production; ask in the team channel first.
