# Repo Layout + Alpha Clone Convention

This repo is intended to be worked on in a **shared/canonical product-repo location** within the 8825 workspace.

## Canonical location

Clone product repos under the org-level `apps/` folder:

- `8825-Team/apps/<repo-name>`

For Maestra:

- `8825-Team/apps/maestra.8825.systems`

### Why

- Prevents a user-specific folder from becoming the accidental source of truth
- Keeps paths consistent across machines and alpha users
- Makes CI/CD and deployment deterministic
- Reduces hardcoded path problems

## Alpha user clones (separate concept)

Alpha user clones are for **user-specific tooling** (local services, configs, caches, logs), not for canonical product repos:

- `8825-Team/users/<alpha_user>/...`

## Multi-user development (recommended)

Use one canonical clone under `apps/` and optionally add **git worktrees** for per-user isolated working directories.

### 1) Canonical clone (one-time)

```bash
git clone https://github.com/Jh-justinHarmon/maestra.8825.systems apps/maestra.8825.systems
```

### 2) Optional per-user worktree

From inside `apps/maestra.8825.systems`:

```bash
git worktree add ../../users/alpha_sm/worktrees/maestra.8825.systems -b alpha_sm
```

## Maestra config

### Backend URL

This repo uses Vite env configuration:

- `VITE_MAESTRA_API=https://maestra-backend-8825-systems.fly.dev`

If unset, the app falls back to the production backend URL.
