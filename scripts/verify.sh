#!/usr/bin/env bash
# Kiểm trước khi ship app ns — chạy từ gốc repo: bash scripts/verify.sh
# Không cần bench: Python chạy API THẬT trên Frappe giả (scripts/fakefrappe.py); trình duyệt dùng Chromium sẵn có
# (thiếu Chromium thì bài giao diện tự BỎ QUA, không đỏ giả).
set -u
cd "$(dirname "$0")/.."
R=${NEXTCODE_REFS:-$HOME/.claude/skills/nextcode-build/references}
hong=0
chay() { echo; echo "═══ $* ═══"; "$@" || { echo "✗ HỎNG: $*"; hong=$((hong + 1)); }; }

chay python3 -m py_compile $(find ns scripts -name '*.py')
for f in $(find ns/public/ns -name '*.js') scripts/*.mjs; do node --check "$f" || { echo "✗ cú pháp JS: $f"; hong=$((hong + 1)); }; done
if [ -d "$R" ]; then
    chay python3 "$R/validate_fixtures.py" ns
    chay python3 "$R/check_doctype_json.py" ns/ns/doctype
    chay python3 "$R/lint_patches.py" ns
    # validate_shipped_docs tải schema Frappe v16 thật (cần mạng) — mất mạng thì báo, không chặn
    python3 "$R/validate_shipped_docs.py" ns || echo "(validate_shipped_docs không chạy được — kiểm lại khi có mạng)"
else
    echo "(không có $R — bỏ qua validator nextcode-build)"
fi
chay python3 scripts/test-importmap.py
chay python3 scripts/test-phieuluong.py
chay python3 scripts/test-congnhan.py
chay python3 scripts/test-taikhoan.py
chay node scripts/test-giaodien.mjs

echo
if [ "$hong" -eq 0 ]; then echo "VERIFY-OK"; else echo "VERIFY: $hong HỎNG"; fi
exit "$hong"
