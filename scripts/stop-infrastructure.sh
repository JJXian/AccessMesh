#!/usr/bin/env bash

set -euo pipefail

# 只停止本项目启动的基础设施服务，不删除容器或持久化数据。
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

docker compose stop postgres opa
