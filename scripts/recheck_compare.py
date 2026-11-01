"""For each flagged (setup:step:metric) in a recheck list, show the values in the original run and
each recheck run, and whether the difference reproduced in every run.

Usage: recheck_compare.py <recheck list> <orig outdir> <recheck outdir> [...]
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util

spec = importlib.util.spec_from_file_location('an', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'analyze_nav.py'))
an = importlib.util.module_from_spec(spec)
sys.argv_saved = sys.argv
src = open(spec.origin).read().replace('\nmain()\n', '\n')
exec(compile(src, spec.origin, 'exec'), an.__dict__)


def feats(outdir, setup, pid):
    f = os.path.join(outdir, setup, pid + '.json')
    if not os.path.exists(f):
        return None
    r = json.load(open(f))
    if r.get('error'):
        return None
    return an.features(r)[0]


lst, dirs = sys.argv[1], sys.argv[2:]
summary = []
for line in open(lst):
    if not line.strip():
        continue
    url, reasons = line.split()
    pid = hashlib.sha1(url.encode()).hexdigest()[:10]
    print('##', pid, url[:90])
    for reason in reasons.split(','):
        setup, step, metric = reason.split(':')
        row, repro = [], []
        for d in dirs:
            fa, fx, fc = feats(d, 'A', pid), feats(d, setup, pid), feats(d, 'C', pid)
            va = (fa or {}).get(step, {}).get(metric)
            vx = (fx or {}).get(step, {}).get(metric)
            vc = (fc or {}).get(step, {}).get(metric)
            row.append(f'A={va} {setup}={vx}' + (f' C={vc}' if setup == 'B' else ''))
            if fa and fx and step in fa and step in fx:
                repro.append(not an.same(metric, va, vx) and (setup != 'B' or an.same(metric, va, vc)))
        ok = bool(repro) and all(repro) and len(repro) == len(dirs)
        summary.append((ok, url, reason))
        print(f'   {"REPRO" if ok else "no   "} {reason:28} ' + ' | '.join(row)[:300])
print('\nreproduced in every run:')
for ok, url, reason in summary:
    if ok:
        print('  ', reason, url[:90])
