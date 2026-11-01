"""Client-pages in the 10k sample whose Navigation API snippets use a given feature, by source.
Usage: feature_usage.py > data/feature-usage.txt"""
import collections, json, re
from urllib.parse import urlsplit
rows = json.load(open('queries/02-sample10k-snippets.json'))
for tok in ['userInitiated', 'hasUAVisualTransition', 'precommitHandler', r'navigation\.back\(', r'traverseTo\(', r'\.finished', 'focusReset', 'downloadRequest', 'formData', 'canGoBack', r'activation']:
    pat = re.compile(tok); pages = collections.defaultdict(set)
    for r in rows:
        if any(pat.search(s) for s in r['snippets']):
            h = urlsplit(r['url']).hostname
            pages['same-origin' if h == urlsplit(r['page']).hostname else h].add((r['client'], r['page']))
    tot = len(set().union(*pages.values())) if pages else 0
    print(f'{tot:5} {tok:24}', ', '.join(f'{k}({len(v)})' for k, v in sorted(pages.items(), key=lambda kv: -len(kv[1]))[:6]))
