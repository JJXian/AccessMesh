#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$PROJECT_DIR/apps/web"
cd "$WEB_DIR"

if [[ ! -d node_modules ]]; then
  npm install
fi

echo "AccessMesh Web: http://localhost:5173"
exec npm run dev -- --host localhost
