#!/bin/bash
# Deployment script, run on the EC2 instance.
#
# Invoked two ways:
#   - automatically by .github/workflows/cd.yml after CI passes on main
#   - manually:  bash ~/deploy.sh
#
# Safe to run repeatedly: it makes the server match origin/main exactly,
# rebuilds, and refuses to report success unless the app answers afterwards.
set -euo pipefail

REPO_DIR="$HOME/AI-Study-Assistant"
COMPOSE_DIR="$REPO_DIR/project"
HEALTH_URL="http://127.0.0.1:8000/api/health/"

echo "==> Fetching latest code"
cd "$REPO_DIR"
git fetch --all --prune

# Deliberately a hard reset rather than `git pull`: the server is a deploy
# target, not a workspace. Any local edit here is drift that should be
# thrown away, and a pull would fail on conflicts instead. Untracked files
# are NOT touched, so backend/.env survives.
git reset --hard origin/main

echo "==> Rebuilding and restarting containers"
cd "$COMPOSE_DIR"
docker compose up -d --build

echo "==> Removing unused images"
# Old image layers accumulate on every deploy; the disk is only 30 GB.
docker image prune -f

echo "==> Waiting for the app to become healthy"
for attempt in $(seq 1 30); do
    if curl -fsS "$HEALTH_URL" > /dev/null 2>&1; then
        echo "==> Healthy after ${attempt} attempt(s)"
        docker compose ps
        exit 0
    fi
    sleep 5
done

echo "==> FAILED: app did not become healthy within 150 seconds"
docker compose ps
docker compose logs --tail=50 backend
exit 1
