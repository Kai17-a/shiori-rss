#!/usr/bin/env bash
set -euo pipefail

api_base_url="${1:-${API_BASE_URL:-http://localhost:8000}}"
bookmark_url="${2:-${BOOKMARK_URL:-https://example.com/?popup_api_check=$(date +%s)}}"
bookmark_title="${3:-${BOOKMARK_TITLE:-Example title}}"
bookmark_description="${4:-${BOOKMARK_DESCRIPTION:-Example description}}"
folder_id="${5:-${FOLDER_ID:-null}}"
tag_ids_csv="${6:-${TAG_IDS:-}}"

green=$'\033[32m'
red=$'\033[31m'
reset=$'\033[0m'

if [[ -n "${API_BASE_URL:-}" ]]; then
  api_base_url="${API_BASE_URL}"
fi

if [[ -n "${BOOKMARK_URL:-}" ]]; then
  bookmark_url="${BOOKMARK_URL}"
fi

if [[ -n "${BOOKMARK_TITLE:-}" ]]; then
  bookmark_title="${BOOKMARK_TITLE}"
fi

if [[ -n "${BOOKMARK_DESCRIPTION:-}" ]]; then
  bookmark_description="${BOOKMARK_DESCRIPTION}"
fi

if [[ -n "${FOLDER_ID:-}" ]]; then
  folder_id="${FOLDER_ID}"
fi

if [[ -n "${TAG_IDS:-}" ]]; then
  tag_ids_csv="${TAG_IDS}"
fi

trim_trailing_slash() {
  local value="${1}"
  while [[ "${value}" == */ ]]; do
    value="${value%/}"
  done
  printf '%s' "${value}"
}

api_base_url="$(trim_trailing_slash "${api_base_url}")"

json_escape() {
  python3 - <<'PY' "$1"
import json
import sys

print(json.dumps(sys.argv[1]))
PY
}

tag_ids_json="[]"
if [[ -n "${tag_ids_csv}" ]]; then
  IFS=',' read -r -a tag_ids <<< "${tag_ids_csv}"
  tag_ids_json="["
  for index in "${!tag_ids[@]}"; do
    if [[ "${index}" -gt 0 ]]; then
      tag_ids_json+=","
    fi
    tag_ids_json+="${tag_ids[index]}"
  done
  tag_ids_json+="]"
fi

request_body="$(printf '{"url":%s,"title":%s,"description":%s,"folder_id":%s,"tag_ids":%s}' \
  "$(json_escape "${bookmark_url}")" \
  "$(json_escape "${bookmark_title}")" \
  "$(json_escape "${bookmark_description}")" \
  "${folder_id}" \
  "${tag_ids_json}")"

check() {
  local method="${1}"
  local path="${2}"
  local expected="${3}"
  local extra_args=("${@:4}")

  local response_file
  response_file="$(mktemp)"
  local status
  local request_url="${api_base_url}${path}"

  printf '\n[%s %s]\n' "${method}" "${request_url}"
  printf 'expected: %s\n' "${expected}"

  status="$(
    curl -sS -o "${response_file}" -w '%{http_code}' \
      -X "${method}" \
      "${request_url}" \
      "${extra_args[@]}"
  )"

  if [[ "${status}" != "${expected}" ]]; then
    printf '%sresult: %s (mismatch)%s\n' "${red}" "${status}" "${reset}" >&2
    printf 'response body:\n' >&2
    cat "${response_file}" >&2
    rm -f "${response_file}"
    exit 1
  fi

  printf '%sresult: %s%s\n' "${green}" "${status}" "${reset}"
  if [[ -s "${response_file}" ]]; then
    printf 'response body:\n'
    cat "${response_file}"
    printf '\n'
  else
    printf 'response body: <empty>\n'
  fi

  rm -f "${response_file}"
}

echo "API base: ${api_base_url}"
echo "Bookmark URL: ${bookmark_url}"

check GET "/health" 200
check GET "/folders" 200
check GET "/tags" 200
check POST "/bookmarks" 201 \
  -H 'Content-Type: application/json' \
  --data "${request_body}"
check PATCH "/bookmarks/by-url?url=$(python3 - <<'PY' "$bookmark_url"
import urllib.parse
import sys

print(urllib.parse.quote(sys.argv[1], safe=''))
PY
)" 200 \
  -H 'Content-Type: application/json' \
  --data "$(printf '{"title":%s,"description":%s,"folder_id":%s,"tag_ids":%s}' \
    "$(json_escape "${bookmark_title}")" \
    "$(json_escape "${bookmark_description}")" \
    "${folder_id}" \
    "${tag_ids_json}")"
check DELETE "/bookmarks?url=$(python3 - <<'PY' "$bookmark_url"
import urllib.parse
import sys

print(urllib.parse.quote(sys.argv[1], safe=''))
PY
)" 204
