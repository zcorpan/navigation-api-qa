#!/bin/zsh
cd "$(dirname "$0")"
.venv/bin/python -I testrun.py tests/entries-after-reload.html "tests/react-indicator-cross-document-click.html?slow=1&ms=150&how=location" --setups D > tests/results/safari2.log 2>&1
.venv/bin/python -I navqa.py run D samples/batch2-active.txt out/b2/D --workers 1 --plan-from out/b2/A >> out/b2/D.log 2>&1
echo safari-queue2-done
