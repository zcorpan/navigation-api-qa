import collections, json, re, sys
from urllib.parse import urlsplit

rows = json.load(open(sys.argv[1]))
tok = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 25
pat = re.compile(tok)
src = collections.defaultdict(set)
ex = {}
for r in rows:
    hit = [s for s in r['snippets'] if pat.search(s)]
    if not hit:
        continue
    u = urlsplit(r['url'])
    path = re.sub(r'[0-9a-f]{8,}|\d+', 'N', u.path)
    key = (u.hostname if u.hostname != urlsplit(r['page']).hostname else 'SAME-ORIGIN') + ' ' + ('/'.join(path.split('/')[:3]) if u.hostname != urlsplit(r['page']).hostname else r['type'])
    src[key].add((r['client'], r['page']))
    ex.setdefault(key, hit[0])
for k in sorted(src, key=lambda k: -len(src[k]))[:n]:
    print(f'{len(src[k]):6} {k}\n        {ex[k][:330]!r}')
