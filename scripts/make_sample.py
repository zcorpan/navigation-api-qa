"""Seeded stratified sample of desktop pages from data/pages_libs.json.

Each page's stratum is its first library in PRIORITY order (libraries that change navigation
behavior first, passive listeners and readers last). Pages already in any earlier batch file are
skipped, so later batches with the same seed extend the same order.

Usage: make_sample.py <seed> <out.txt> <exclude files...> -- stratum=n ...
"""
import hashlib
import json
import sys

PRIORITY = [
    'steam', 'back-intercept', 'transcend-airgap', 'geoedge', 'angular-platform-navigation', 'qwik-city',
    'nextjs-activation', 'react-transition-indicator', 'react-view-transition', 'activation-read', 'perimeterx',
    'meta-rsrc', 'shopify-wpm', 'amplitude', 'dynatrace', 'contentsquare', 'debugbear', 'membrana', 'iadvize', 'mgid',
    'klaviyo', 'pushly', 'tiktok', 'stay22', 'seedtag', 'doubleverify', 'rokt', 'ezoic', 'nitrous', 'other',
    'cloudflare-beacon', 'gpt', 'gtm-entries', 'cloudflare-challenge', 'ias-detect', 'adscore-fp',
]
NONE = {'youtube-custom-event', 'sw-false-positive', 'convert-fp'}


def stratum(libs):
    for p in PRIORITY:
        if p in libs:
            return p
    return None


def main():
    seed, out = sys.argv[1], sys.argv[2]
    i = sys.argv.index('--')
    exclude_files, quotas = sys.argv[3:i], dict(a.split('=') for a in sys.argv[i + 1:])
    exclude = set()
    for f in exclude_files:
        exclude |= {l.split()[0] for l in open(f) if l.strip() and not l.startswith('#')}
    pages = [p for p in json.load(open('data/pages_libs.json')) if p['client'] == 'desktop']
    by = {}
    for p in pages:
        s = stratum(set(p['libs']) - NONE)
        if s:
            by.setdefault(s, []).append(p)
    lines = []
    for s, n in quotas.items():
        cand = sorted(by.get(s, []), key=lambda p: hashlib.sha1((p['page'] + seed).encode()).hexdigest())
        cand = [p for p in cand if p['page'] not in exclude][:int(n)]
        for p in cand:
            lines.append(f"{p['page']} {s} {p['rank']}")
        print(f'{s}: {len(cand)} of {len(by.get(s, []))}')
    open(out, 'w').write('\n'.join(lines) + '\n')
    print(len(lines), 'pages')


main()
