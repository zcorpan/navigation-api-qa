"""Recompute every number the README and findings cite, from committed files.
Usage: recount.py (from the repo root)"""
import collections
import csv
import glob
import json
import os


def rows(path):
    return list(csv.DictReader(open(path)))


print('## HTTP Archive')
c = rows('queries/01-counter-pages.csv')
cnt = collections.Counter((r['client'], r['is_root_page']) for r in c)
print('kNavigationAPI (4056) pages, 2026-10-01:', dict(cnt), 'rank<=100k:', sum(1 for r in c if int(r['rank']) <= 100000))
pages = {r['client']: int(r['f0_']) for r in rows('data/sample10k-pages.csv')}
print('requests_10k pages:', pages)
lib = rows('queries/02-sample10k-pages.csv')
print('client-pages with a Navigation API token:', len(lib), collections.Counter(r['client'] for r in lib))
libcount = collections.Counter(l for r in lib for l in r['libs'].split())
for k in ('gtm-entries', 'cloudflare-beacon', 'gpt', 'react-transition-indicator', 'react-view-transition',
          'activation-read', 'nextjs-activation', 'back-intercept', 'geoedge', 'steam'):
    print(f'  {k}: {libcount[k]}')
active = json.load(open('data/active_pages.json'))
print('desktop pages with active calls (intercept/navigate/updateCurrentEntry/traverseTo/back/precommitHandler):', len(active))

print('\n## Samples')
for b in ('batch1', 'batch2'):
    s = [l.split() for l in open(f'samples/{b}.txt') if l.strip()]
    print(b, len(s), 'pages;', dict(collections.Counter(x[1].split(':')[0] for x in s).most_common(8)))

print('\n## Visits')
for b in ('b1', 'b2'):
    for s in ('A', 'A2', 'B', 'C', 'D'):
        recs = [json.load(open(f)) for f in glob.glob(f'out/{b}/{s}/*.json')]
        err = sum(1 for r in recs if r.get('error'))
        print(f'  {b}/{s}: {len(recs)} records, {err} visit errors')

print('\n## Active API use seen in Chrome traces (A)')
for b in ('b1', 'b2'):
    k = collections.Counter()
    for f in glob.glob(f'out/{b}/A/*.json'):
        r = json.load(open(f))
        kinds = set()
        for st in r.get('steps', []):
            for e in (st.get('log') or []) + ((st.get('prev') or {}).get('log') or []):
                if e['k'] == 'intercept':
                    kinds.add('intercept')
                if e['k'] == 'call' and e.get('m') != 'entries':
                    kinds.add('call:' + e['m'])
                if e['k'] == 'navigate' and e.get('info') == '"react-transition"':
                    kinds.add('react-transition')
                if e['k'] == 'listen':
                    kinds.add('listen')
        k.update(kinds)
    print(' ', b, dict(k))

print('\n## Crash (finding 01)')
for f in sorted(glob.glob('data/crash/*.jsonl')):
    rs = [json.loads(l) for l in open(f)]
    dead = sum(1 for r in rs if r.get('diedAt') and not ('neterror' in (r.get('error') or '')))
    net = sum(1 for r in rs if 'neterror' in (r.get('error') or ''))
    print(f'  {os.path.basename(f)}: {len(rs)} pages, browser died: {dead}, network errors: {net}')

print('\n## Flags')
for b in ('b1', 'b2'):
    fl = json.load(open(f'out/{b}/flags.json'))
    bc = sum(1 for f in fl if any(d['setup'] == 'B' and d.get('C_same_as_A') for d in f['diffs']))
    print(f'  {b}: {len(fl)} pages compared, {bc} with a Firefox diff the API-off control does not share')

print('\n## bfcache on back/forward (pageshow persisted), per setup')
src = open('analyze_nav.py').read().replace('\nmain()\n', '\n')
an = {}
exec(compile(src, 'analyze_nav.py', 'exec'), an)
for label, dirs in [('batches 1+2', [('A', 'out/b1/A'), ('A', 'out/b2/A'), ('B', 'out/b1/B'), ('B', 'out/b2/B'), ('C', 'out/b1/C'), ('C', 'out/b2/C'), ('D', 'out/b1/D'), ('D', 'out/b2/D')]),
                    ('bf (80 pages, pointer-action clicks; A3 = Chrome with bfcache)', [('A3', 'out/bf/A3'), ('B', 'out/bf/B'), ('C', 'out/bf/C')])]:
    cnt = collections.Counter()
    for s, d in dirs:
        for f in glob.glob(f'{d}/*.json'):
            r = json.load(open(f))
            if r.get('error'):
                continue
            fe = an['features'](r)[0]
            for st in ('back', 'forward'):
                v = (fe.get(st) or {}).get('bfcache')
                if v is not None:
                    cnt[(s, st, v)] += 1
    print(' ', label)
    for s in sorted({k[0] for k in cnt}):
        print('    ', s, {st: f'{cnt[(s, st, True)]}/{cnt[(s, st, True)] + cnt[(s, st, False)]}' for st in ('back', 'forward')})
