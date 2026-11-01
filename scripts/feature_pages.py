"""Desktop pages in the 10k sample whose bodies use a given Navigation API feature (regex on
snippets), excluding given library hosts. Prints page, matched source, rank.
Usage: feature_pages.py <regex> [exclude-host-regex]"""
import json, re, sys
from urllib.parse import urlsplit
rows = json.load(open('queries/02-sample10k-snippets.json'))
pat = re.compile(sys.argv[1])
ex = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
seen = set()
for r in rows:
    if r['client'] != 'desktop' or r['page'] in seen:
        continue
    if ex and ex.search(r['url']):
        continue
    if any(pat.search(s) for s in r['snippets']):
        seen.add(r['page'])
        print(r['page'], urlsplit(r['url']).hostname, r['rank'])
