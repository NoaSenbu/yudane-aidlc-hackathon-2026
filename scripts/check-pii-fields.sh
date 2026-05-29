#!/usr/bin/env bash
# CalendarEvent への PII フィールド（title/body/attendees）混入を検出して fail する。
# FR-CAL-05 / NG-7 / api-contracts.md §9.1 / business-rules PII-09 / API-10。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA_FILE="${REPO_ROOT}/shared/schema/components/schemas/common.yaml"

if [[ ! -f "${SCHEMA_FILE}" ]]; then
  echo "ERROR: スキーマファイルが見つかりません: ${SCHEMA_FILE}" >&2
  exit 1
fi

# CalendarEvent 定義ブロック内に禁止フィールドが現れないか検査
# （シンプルな実装: CalendarEvent: 以降の properties 直下に title/body/attendees がないか）
forbidden='title|body|attendees'

# CalendarEvent ブロックを抽出（次のトップレベルキーまで）
block="$(awk '/^CalendarEvent:/{f=1} f{print} /^[A-Za-z]/ && !/^CalendarEvent:/ && f && NR>1{ if ($0 !~ /^[[:space:]]/) exit }' "${SCHEMA_FILE}")"

if echo "${block}" | grep -E "^[[:space:]]+(${forbidden}):" >/dev/null 2>&1; then
  echo "ERROR: CalendarEvent に禁止フィールド (${forbidden}) が含まれています。" >&2
  echo "       FR-CAL-05 / NG-7 によりカレンダー予定本文の送信は禁止です。" >&2
  exit 1
fi

echo "OK: CalendarEvent に PII 禁止フィールドはありません。"
