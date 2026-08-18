#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  if ! command -v python3.12 >/dev/null 2>&1; then
    echo "未找到 Python 3.12，请先安装 Python 3.12。" >&2
    exit 1
  fi
  python3.12 -m venv .venv
fi

if ! .venv/bin/python -c 'import accessmesh, uvicorn' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -e '.[dev]'
fi

echo "正在启动 PostgreSQL 和 OPA..."
docker compose up -d --wait postgres opa

export DATABASE_URL='postgresql+asyncpg://accessmesh:accessmesh@localhost:55432/accessmesh'
export OPA_URL='http://localhost:8181'

echo "正在执行数据库迁移..."
.venv/bin/alembic upgrade head

echo "AccessMesh API: http://localhost:8000/docs"
exec .venv/bin/python -m uvicorn accessmesh.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000
