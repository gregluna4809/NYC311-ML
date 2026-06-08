#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

echo "[$(timestamp)] Starting NYC311 data refresh"
cd "${PROJECT_ROOT}"

docker compose run --rm dataloader

echo "[$(timestamp)] NYC311 data refresh completed"
