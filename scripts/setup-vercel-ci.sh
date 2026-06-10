#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPO="${GITHUB_REPO:-lisss/dday}"
PROJECT_NAME="${VERCEL_PROJECT_NAME:-dday}"
VERCEL_AUTH_FILE="auth.json"

echo "Setting up Vercel CI for $REPO"

if ! vercel whoami >/dev/null 2>&1; then
  echo "Not logged in to Vercel. Run: vercel login"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Not logged in to GitHub. Run: gh auth login"
  exit 1
fi

if [ ! -f .vercel/project.json ]; then
  echo "Linking Vercel project '$PROJECT_NAME'..."
  vercel link --yes --project "$PROJECT_NAME"
fi

ORG_ID="$(python3 -c "import json; print(json.load(open('.vercel/project.json'))['orgId'])")"
PROJECT_ID="$(python3 -c "import json; print(json.load(open('.vercel/project.json'))['projectId'])")"

if [ -z "${VERCEL_TOKEN:-}" ] && [ -f "$VERCEL_AUTH_FILE" ]; then
  VERCEL_TOKEN="$(python3 -c "import json; print(json.load(open('$VERCEL_AUTH_FILE')).get('token', ''))")"
fi

if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "Create a token at https://vercel.com/account/settings/tokens"
  echo "Then run: VERCEL_TOKEN=your_token $0"
  exit 1
fi

echo "Setting GitHub secrets on $REPO..."
gh secret set VERCEL_TOKEN --repo "$REPO" --body "$VERCEL_TOKEN"
gh secret set VERCEL_ORG_ID --repo "$REPO" --body "$ORG_ID"
gh secret set VERCEL_PROJECT_ID --repo "$REPO" --body "$PROJECT_ID"

echo "Done."
echo "  VERCEL_ORG_ID=$ORG_ID"
echo "  VERCEL_PROJECT_ID=$PROJECT_ID"
echo "Commit and push to trigger a deploy."
