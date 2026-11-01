"""Compare setups per page and step, flag differences for review.

Usage: analyze_nav.py <outdir> [<outdir> ...] > analysis/flags.txt  (also writes <outdir>/flags.json)

For each step, a metric differs for setup X when A and A2 agree and X doesn't. The flag records
whether C (Firefox, API off) agrees with A, and whether the page used the Navigation API (trace).
"""
import collections
import json
import os
import re
import sys

SETUPS = ['A', 'A2', 'B', 'C', 'D']
API_KINDS = {'call', 'listen', 'intercept', 'scroll', 'get'}


def norm_err(e):
    e = re.sub(r'[a-z][a-z0-9+.-]*://[^\s\'")]+', 'URL', e)
    e = re.sub(r'\b[0-9a-f]{6,}\b', 'H', e)
    e = re.sub(r'\d+', 'N', e)
    return e[:160]


def load(outdir):
    pages = collections.defaultdict(dict)
    for s in SETUPS:
        d = os.path.join(outdir, s)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.json'):
                r = json.load(open(os.path.join(d, f)))
                pages[r['id']][s] = r
    return pages


def step_events(steps):
    """Per step, the trace entries logged since the previous step."""
    out = []
    seen = 0
    for i, s in enumerate(steps):
        log = s.get('log') or []
        if i == 0 or not s.get('sameDoc'):
            prev = (s.get('prev') or {}).get('log') or []
            ev = prev[seen:] if i else []
            ev = ev + log
        else:
            ev = log[seen:]
        seen = len(log)
        out.append(ev)
    return out


def features(rec):
    steps = rec.get('steps') or []
    evs = step_events(steps)
    base = steps[0] if steps else {}
    feats = {}
    api = set()
    for s, ev in zip(steps, evs):
        name = s['step']
        if s.get('skipped'):
            feats[name] = {'skipped': True}
            continue
        nav = s.get('nav') if isinstance(s.get('nav'), dict) else {}
        navs = [e for e in ev if e.get('k') == 'navigate']
        intercepts = [e for e in ev if e.get('k') == 'intercept']
        errs = sorted({norm_err(e.get('e', '')) for e in ev if e.get('k') in ('error', 'rejection')})
        nav_errs = sorted({e['k'] + ' ' + (e.get('e') or '').split(':')[0] for e in ev if e.get('k') in ('navigateerror', 'committed-reject', 'finished-reject')})
        err_names = sorted({(e.get('e') or '').split(':')[0][:40] for e in ev if e.get('k') in ('error', 'rejection')})
        for e in ev:
            if e.get('k') in API_KINDS:
                api.add(e['k'] + ':' + str(e.get('m')))
        feats[name] = {
            'path': re.sub(r'[?#].*', '', s.get('url') or ''),
            'sameDoc': s.get('sameDoc') if name != 'load' else None,
            'histDelta': (s.get('histLen') or 0) - (base.get('histLen') or 0),
            'navLen': nav.get('len'),
            'navIdx': nav.get('idx'),
            'scrollY': s.get('scrollY'),
            'stuck': s.get('settle') is None and name != 'load',
            'transition': bool(nav.get('transition')),
            'navigateUserIntercepts': sum(1 for e in navs if e.get('info') != 'react-transition'),
            'intercepted': len(intercepts),
            'errs': errs,
            'navErrs': nav_errs,
            'errNames': err_names,
            'textLen': s.get('textLen') or 0,
            'titleHash': s.get('titleHash'),
            'click': s.get('click'),
        }
    return feats, api


def same(metric, a, b):
    if a is None or b is None:
        return a == b
    if metric == 'scrollY':
        return abs(a - b) <= max(60, 0.05 * max(abs(a), abs(b)))
    if metric == 'textLen':
        return abs(a - b) <= max(200, 0.15 * max(a, b))
    return a == b


METRICS = ['path', 'sameDoc', 'histDelta', 'navLen', 'navIdx', 'scrollY', 'stuck', 'transition', 'intercepted', 'textLen', 'titleHash']


def compare(pages):
    flags = []
    for pid, recs in pages.items():
        if 'A' not in recs:
            continue
        F = {}
        api = {}
        for s, r in recs.items():
            if 'error' in r:
                F[s] = None
            else:
                F[s], api[s] = features(r)
        page = recs['A']['page']
        out = {'id': pid, 'page': page, 'errors': {s: r.get('error') for s, r in recs.items() if r.get('error')},
               'api': sorted(api.get('A', set()) | api.get('B', set())), 'diffs': []}
        fa, fa2 = F.get('A'), F.get('A2')
        if not fa or not fa2:
            flags.append(out)
            continue
        needs = {'link2': 'link', 'back': 'link', 'back3': 'link2', 'forward': 'back', 'back2': 'fragment'}
        moved = {k: (not v.get('skipped')) and (v.get('path') != fa.get('load', {}).get('path') or v.get('histDelta', 0) > 0)
                 for k, v in fa.items() if k in ('link', 'link2')}
        for step in fa:
            if step in needs and fa.get(needs[step], {}).get('skipped'):
                continue
            if step in ('back', 'forward') and not moved.get('link', True):
                continue
            if step == 'back3' and not moved.get('link2', True):
                continue
            a, a2 = fa[step], fa2.get(step)
            if not a2 or a.get('skipped') or a2.get('skipped'):
                continue
            for x in ('B', 'C', 'D'):
                fx = F.get(x)
                if not fx or step not in fx or fx[step].get('skipped'):
                    continue
                for m in METRICS:
                    if same(m, a.get(m), a2.get(m)) and not same(m, a.get(m), fx[step].get(m)):
                        out['diffs'].append({'setup': x, 'step': step, 'metric': m, 'A': a.get(m), x: fx[step].get(m)})
                if x == 'B':
                    # same engine with the API off is the reference for Firefox's error messages
                    fc = (F.get('C') or {}).get(step) or {}
                    new = [e for e in fx[step]['errs'] if e not in set(fc.get('errs') or [])]
                    if new and not fc.get('skipped') and fc:
                        out['diffs'].append({'setup': x, 'step': step, 'metric': 'newErrors', x: new, 'A_errNames': sorted(set(a['errNames']) | set(a2['errNames']))})
                elif x == 'D':
                    new = [e for e in fx[step]['errNames'] if e not in set(a['errNames']) | set(a2['errNames'])]
                    if new:
                        out['diffs'].append({'setup': x, 'step': step, 'metric': 'newErrors', x: new})
                ne = [e for e in fx[step]['navErrs'] if e not in set(a['navErrs']) | set(a2['navErrs'])]
                if ne:
                    out['diffs'].append({'setup': x, 'step': step, 'metric': 'navErrors', x: ne})
        # attribution for Firefox diffs: C agreeing with A means the API path made the difference
        cdiff = {(d['step'], d['metric']) for d in out['diffs'] if d['setup'] == 'C'}
        fc = F.get('C') or {}
        for d in out['diffs']:
            if d['setup'] == 'B':
                cstep = fc.get(d['step'])
                d['C_same_as_A'] = None if not cstep or cstep.get('skipped') else (d['step'], d['metric']) not in cdiff
        out['skippedSteps'] = {s: [k for k, v in f.items() if v.get('skipped')] for s, f in F.items() if f}
        flags.append(out)
    return flags


def main():
    allflags = []
    for outdir in sys.argv[1:]:
        flags = compare(load(outdir))
        json.dump(flags, open(os.path.join(outdir, 'flags.json'), 'w'), indent=1)
        allflags += flags
    cnt = collections.Counter()
    for f in allflags:
        for d in f['diffs']:
            if d['setup'] == 'C':
                continue
            cnt[(d['setup'], d['metric'], d.get('C_same_as_A'))] += 1
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(v, k)
    for f in allflags:
        ds = [d for d in f['diffs'] if d['setup'] != 'C' and not (d['setup'] == 'B' and d.get('C_same_as_A') is False and d['metric'] not in ('newErrors', 'navErrors'))]
        if ds or f['errors']:
            print('\n##', f['id'], f['page'][:100])
            if f['errors']:
                print('   errors:', f['errors'])
            print('   api:', ' '.join(f['api'])[:300])
            for d in ds:
                print('   ', d['setup'], d['step'], d['metric'], 'A=' + str(d.get('A'))[:120], d['setup'] + '=' + str(d.get(d['setup']))[:240],
                      '' if d['setup'] != 'B' else 'C_same_as_A=' + str(d.get('C_same_as_A')))


main()
