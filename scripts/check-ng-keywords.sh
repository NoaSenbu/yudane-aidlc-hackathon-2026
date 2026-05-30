#!/usr/bin/env bash
# Property 4 / NG-6 静的検証 — 30 通知テンプレートに脅迫・罪悪感強要キーワードが含まれないことを CI で検証。
#
# 設計: aidlc-docs/construction/unit-5-cart-intercept/functional-design/functional-design.md
#       Property 4: NG-6 脅迫禁止コピーの遵守

set -eu

TEMPLATES_FILE="backend/src/cart/notification_templates.py"

if [ ! -f "${TEMPLATES_FILE}" ]; then
  echo "Error: ${TEMPLATES_FILE} not found" >&2
  exit 1
fi

# NG-6 禁止ワード（notification_templates.py の NG6_FORBIDDEN_WORDS と同期）
NG6_WORDS=(
  "ストレス悪化"
  "罪悪感"
  "失敗"
  "後悔するよ"
  "ダメな人"
  "情けない"
  "恥ずかしい"
  "残念"
  "やっぱりだめ"
  "向いてない"
  "我慢できない"
  "弱い"
  "どうせ"
  "結局"
  "意志が弱い"
)

violations=0
# NG6_FORBIDDEN_WORDS の定義行を除外するため、TEMPLATES_30M / TEMPLATES_6H / TEMPLATES_24H のみ抽出
# 簡略化: NG6_FORBIDDEN_WORDS タプルの開始行から終了行までを除外
START_LINE=$(grep -n "NG6_FORBIDDEN_WORDS:" "${TEMPLATES_FILE}" | head -1 | cut -d: -f1)
END_LINE=$(awk "/^NG6_FORBIDDEN_WORDS:/,/^\)$/{print NR; if (\$0 ~ /^\\)$/) exit}" "${TEMPLATES_FILE}" | tail -1)

if [ -z "${START_LINE}" ] || [ -z "${END_LINE}" ]; then
  echo "Error: NG6_FORBIDDEN_WORDS definition not found" >&2
  exit 1
fi

# テンプレート部分のみを抽出（NG6_FORBIDDEN_WORDS 定義 + check_ng6_violation 関数を除外）
TEMPLATE_CONTENT=$(awk "NR < ${START_LINE}" "${TEMPLATES_FILE}")

for word in "${NG6_WORDS[@]}"; do
  # コメント行（# で始まる）と docstring 内の説明文を除外し、テンプレート文字列値のみ検査
  matches=$(echo "${TEMPLATE_CONTENT}" | grep -n "${word}" | grep -v "^[[:space:]]*#" | grep -v '"""' | grep -v '^.*:[[:space:]]*#' || true)
  # さらに 'title' / 'body' を含む辞書値かを確認
  template_matches=$(echo "${matches}" | grep -E '"(title|body)"' || true)
  if [ -n "${template_matches}" ]; then
    echo "❌ NG-6 violation: '${word}' found in template strings:" >&2
    echo "${template_matches}" >&2
    violations=$((violations + 1))
  fi
done

if [ ${violations} -gt 0 ]; then
  echo "❌ ${violations} NG-6 violations detected" >&2
  exit 1
fi

echo "✅ NG-6 check passed: 30 templates clean"
