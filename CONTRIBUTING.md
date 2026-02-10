# Contributing to SigmaVault NAS OS

## Branch Strategy

We use a **feature branch workflow** to keep `main` stable and CI green.

### Quick Reference

```bash
# Start new work
git checkout -b feat/my-feature main

# Work, commit, push to branch
git add . && git commit -m "feat(scope): description"
git push origin feat/my-feature

# When CI is green → squash merge via PR or locally
git checkout main
git merge --squash feat/my-feature
git commit -m "feat(scope): description (#PR)"
git push origin main

# Cleanup
git branch -d feat/my-feature
git push origin --delete feat/my-feature
```

### Branch Naming Convention

| Prefix      | Purpose                  | Example                     |
| ----------- | ------------------------ | --------------------------- |
| `feat/`     | New features             | `feat/compression-zstd`     |
| `fix/`      | Bug fixes                | `fix/rpc-timeout`           |
| `ci/`       | CI/lint fixes            | `ci/golangci-lint-cleanup`  |
| `refactor/` | Code refactoring         | `refactor/engine-handlers`  |
| `docs/`     | Documentation only       | `docs/api-reference`        |
| `perf/`     | Performance improvements | `perf/compression-pipeline` |
| `test/`     | Adding/fixing tests      | `test/integration-suite`    |

### When to Use Feature Branches

**Always use branches for:**

- CI/lint fix sprints (prevents 10+ fix commits on main)
- Multi-step features that may break tests
- Experimental work or prototyping
- Any work that might need multiple push-fix-push cycles

**Direct to `main` is OK for:**

- Single-file documentation updates
- Version bumps
- Trivial one-line config changes that won't break CI

### Workflow for CI Fix Sprints

This is the #1 time-saver. Instead of pushing 11 fix commits to `main`:

```bash
# Create a CI fix branch
git checkout -b ci/lint-cleanup

# Iterate locally — run pre-push checks between fixes
# (The pre-push hook catches issues before they reach CI)
git commit -m "fix: resolve golangci-lint warnings"
git push origin ci/lint-cleanup  # CI runs on branch, main stays clean

# Fix more issues...
git commit -m "fix: resolve remaining lint issues"
git push origin ci/lint-cleanup

# When CI is fully green → squash merge
git checkout main
git merge --squash ci/lint-cleanup
git commit -m "ci: resolve all lint warnings"
git push origin main  # Single clean commit!
```

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type       | Description                 |
| ---------- | --------------------------- |
| `feat`     | New feature                 |
| `fix`      | Bug fix                     |
| `ci`       | CI/CD changes               |
| `docs`     | Documentation               |
| `refactor` | Code refactoring            |
| `test`     | Test additions/fixes        |
| `perf`     | Performance improvements    |
| `chore`    | Maintenance tasks           |
| `style`    | Formatting, no logic change |

### Scopes

| Scope         | Component              |
| ------------- | ---------------------- |
| `api`         | Go API server          |
| `engine`      | Python RPC engine      |
| `desktop`     | Desktop UI             |
| `build`       | Build system, Makefile |
| `security`    | Security/crypto        |
| `compression` | Compression pipeline   |

## Pre-Push Checks

The `.githooks/pre-push` hook automatically runs:

1. Go lint (`golangci-lint`)
2. Go tests
3. Python lint (`ruff`)
4. Python tests
5. Desktop UI tests

Install the hooks:

```bash
git config core.hooksPath .githooks
```

Bypass in emergencies:

```bash
git push --no-verify
```

## Development Setup

```powershell
# Start the full dev stack
.\scripts\dev-start.ps1

# Kill everything
.\scripts\dev-start.ps1 -Kill

# Start only the API (engine already running)
.\scripts\dev-start.ps1 -SkipEngine
```
