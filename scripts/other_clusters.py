import collections, json, re, sys
sys.argv.append('')
exec(open('scripts/classify_libs.py').read().split('\ndef main')[0])
rows = json.load(open('queries/02-sample10k-snippets.json'))
cl = collections.defaultdict(set); ex = {}
for r in rows:
    for snip in r['snippets']:
        if any((u is None or u.search(r['url'])) and (s is None or s.search(snip)) for _, u, s in SIGS):
            continue
        k = re.sub(r'\b[A-Za-z_$][\w$]{0,2}\b', 'I', snip)
        k = re.sub(r'\s+', ' ', k)
        k = k[len(k)//2-50:len(k)//2+50]
        cl[k].add(r['page']); ex.setdefault(k, (r['url'], snip))
for k in sorted(cl, key=lambda k: -len(cl[k]))[:int(sys.argv[1])]:
    print(len(cl[k]), ex[k][0][:100]); print('    ', ex[k][1][:330])
