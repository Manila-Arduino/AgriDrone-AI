# switch_repo.sh — swap your template to a specific repo fast
# usage: ./switch_repo.sh <git-url> [branch]
set -euo pipefail

REPO_URL="${1:?Usage: ./switch_repo.sh <git-url> [branch] }"
BRANCH="${2:-}"

# 1) run from your project folder (the template is already here)
cd "$(dirname "$0")"

# 2) make sure there are no uncommitted changes
git reset --hard
git clean -xfd

if [ -d .git ]; then
  # OPTION A: template kept as a git repo — just repoint and hard reset
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REPO_URL"
  git fetch --all --prune --depth=1
else
  # OPTION B: template shipped as plain files (recommended) — init fresh
  git init
  git add -A && git commit -m "init from SD template"
  git remote add origin "$REPO_URL"
  git fetch --depth=1
fi

# pick default branch if not provided
if [ -z "$BRANCH" ]; then
  BRANCH="$(git remote show origin | sed -n 's/.*HEAD branch: //p')"
  BRANCH="${BRANCH:-main}"
fi

# 3) hard reset to the chosen repo/branch (overwrites template files)
git reset --hard "origin/$BRANCH"

# 4) sync Python deps (uv) — uses cache if prewarmed
uv sync --all-extras --frozen || uv sync

echo "✅ Switched to $REPO_URL@$BRANCH and synced."
