#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${ES_URL:-http://127.0.0.1:9200}"
BASE_URL="${BASE_URL%/}"
INDEX_NAME="rag_chunks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BODY_FILE="${REPO_ROOT}/database/es/rag_chunks.index.json"

echo "Checking ${BASE_URL}/${INDEX_NAME} ..."
code="$(curl -s -o /dev/null -w "%{http_code}" -I "${BASE_URL}/${INDEX_NAME}" || true)"
if [[ "${code}" == "200" ]]; then
  echo "Index '${INDEX_NAME}' already exists. Skip."
  exit 0
fi

echo "Creating index '${INDEX_NAME}' ..."
curl -sS -X PUT "${BASE_URL}/${INDEX_NAME}" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary "@${BODY_FILE}" | head -c 2000
echo
echo "Done."
