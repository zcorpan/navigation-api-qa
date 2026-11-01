"""Differences between engines in navigation infrastructure, independent of the Navigation API:
steps where Chrome (A, A2) agree, Firefox with and without the API (B, C) agree, and B differs
from A. Shows whether Safari TP (D) sides with Chrome or Firefox.
Usage: engine_diffs.py <outdir> ... > analysis/engine-diffs.txt"""
import collections, importlib.util, json, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(HERE, 'analyze_nav.py')).read().replace('\nmain()\n', '\n')
an = {}
exec(compile(src, 'analyze_nav.py', 'exec'), an)
METRICS = ['path', 'sameDoc', 'histDelta', 'navLen', 'navIdx', 'scrollY', 'bfcache', 'histState', 'stuck']
rows = []
for outdir in sys.argv[1:]:
    pages = an['load'](outdir)
    for pid, recs in pages.items():
        F = {}
        for s in ('A', 'A2', 'B', 'C', 'D'):
            r = recs.get(s)
            if r and not r.get('error'):
                F[s] = an['features'](r)[0]
        if not all(k in F for k in ('A', 'A2', 'B', 'C')):
            continue
        fa = F['A']
        moved = {k: (not v.get('skipped')) and (v.get('path') != fa.get('load', {}).get('path') or v.get('histDelta', 0) > 0) for k, v in fa.items() if k in ('link', 'link2')}
        for step, a in fa.items():
            if a.get('skipped') or (step in ('back', 'forward') and not moved.get('link', True)) or (step == 'back3' and not moved.get('link2', True)):
                continue
            vals = {s: F[s].get(step) for s in F}
            if any(v is None or v.get('skipped') for k, v in vals.items() if k != 'D'):
                continue
            for m in METRICS:
                va, va2, vb, vc = (vals[s].get(m) for s in ('A', 'A2', 'B', 'C'))
                if an['same'](m, va, va2) and an['same'](m, vb, vc) and not an['same'](m, va, vb):
                    vd = vals.get('D').get(m) if vals.get('D') and not vals['D'].get('skipped') else 'n/a'
                    side = 'n/a' if vd == 'n/a' else ('D=Chrome' if an['same'](m, va, vd) else 'D=Firefox' if an['same'](m, vb, vd) else 'D=other')
                    rows.append({'outdir': outdir, 'id': pid, 'page': recs['A']['page'], 'step': step, 'metric': m, 'A': va, 'B': vb, 'D': vd, 'side': side})
json.dump(rows, open(os.path.join(HERE, 'data', 'engine_diffs.json'), 'w'), indent=1)
c = collections.Counter((r['metric'], r['step'], r['side']) for r in rows)
pp = collections.defaultdict(set)
for r in rows:
    pp[(r['metric'], r['step'], r['side'])].add(r['page'])
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print(f'{v:4} {len(pp[k]):4} pages  {k}')
