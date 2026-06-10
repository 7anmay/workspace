# AGENTS.md

Guidance for AI agents working in this repository.

## Repository overview

This is an **empty workspace container** for future agentic projects. As of the initial setup, the only tracked file besides this document is `README.md`. There is no application source code, dependency manifest, Docker configuration, CI workflow, or service definition yet.

## Cursor Cloud specific instructions

### Services

| Service | Required? | Notes |
|---------|-----------|-------|
| *(none)* | — | No services are defined. Nothing needs to be started for this repo in its current state. |

When projects are added to this workspace (submodules, monorepo packages, or cloned code), re-evaluate this section and document each service's startup command here.

### Lint / test / build / run

**Not applicable yet.** There are no `package.json` scripts, `Makefile` targets, `pyproject.toml`, or similar tooling configured.

After a project is added, prefer documenting commands by reference (e.g. "see `apps/foo/README.md`") rather than duplicating them here unless there are non-obvious gotchas.

### VM tooling available

The Cloud Agent VM ships with common development tools pre-installed, including:

- **Node.js** (v22 via nvm) with npm, pnpm, and yarn
- **Python 3.12** with pip
- **Rust** (rustc via cargo)
- **Go**
- **Git** and **make**

Docker is not guaranteed to be available unless a future project requires it and the environment is extended.

### Adding a project

Until code lands in this repo, agents should:

1. Confirm whether the user expects code to be cloned from another repository or added as a submodule.
2. Re-run dependency discovery (`README`, lockfiles, `docker-compose`, etc.) once real project files exist.
3. Update this file with service startup and test/lint commands for the new project(s).

### Git

- Default branch: `main`
- Remote: `https://github.com/7anmay/workspace`
- No custom pre-commit or pre-push hooks are configured (only default `.git/hooks/*.sample` files).
