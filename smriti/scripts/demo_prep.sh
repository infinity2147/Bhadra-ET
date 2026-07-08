#!/bin/zsh
# SMRITI demo preparation — run the evening before the demo.
# Regenerates the corpus (so the TK-401 confined-space permit is dated *tomorrow*),
# rebuilds the fabric, warms every agent cache, and leaves the server ready.
set -e
cd "$(dirname "$0")/.."
PY=../.venv/bin/python

echo "==> 1/5 regenerate corpus (permit date = tomorrow)"
$PY scripts/gen_corpus.py

echo "==> 2/5 refresh fabric (incremental: only new pages get visually embedded)"
(cd backend && ../$PY -m smriti.ingest)

echo "==> 3/5 warm lessons-learned patterns + proactive warnings"
(cd backend && ../$PY -c "
from smriti import lessons
lessons.build_patterns(force=True)
ws = lessons.evaluate_upcoming()
print(f'   {len(ws)} proactive warning(s) ready')
")

echo "==> 4/5 warm compliance register"
(cd backend && ../$PY -c "
from smriti import compliance
reg = compliance.build_register(force=True)
gaps = sum(1 for r in reg if r['status']=='gap')
print(f'   {len(reg)} clauses evaluated, {gaps} gaps found')
")

echo "==> 5/5 done. start the server with:"
echo "    cd backend && ../$PY -m uvicorn smriti.api:app --host 0.0.0.0 --port 8000"
echo "    (eval dashboard: $PY eval/harness.py — allow ~45 min)"
