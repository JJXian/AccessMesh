#!/usr/bin/env bash

set -euo pipefail

# 从脚本位置定位前端目录，避免依赖调用者的当前工作目录。
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$PROJECT_DIR/apps/web"
cd "$WEB_DIR"

if [[ ! -d node_modules ]]; then
  # 首次启动才安装依赖，后续直接复用本地依赖目录。
  npm install
fi

echo "AccessMesh Web: http://localhost:5173"
exec npm run dev -- --host localhost
