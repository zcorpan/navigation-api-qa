import collections, json, re, sys

TOK = re.compile(r'currententrychange|navigatesuccess|navigateerror|canIntercept|\bNavigateEvent\b|NavigationHistoryEntry|navigation\.currentEntry|navigation\.entries\(\)|navigation\.transition|navigation\.updateCurrentEntry|navigation\.traverseTo|["\x27]navigation["\x27]\s*in\s*(?:window|self|globalThis)|window\.navigation\b|globalThis\.navigation\b|self\.navigation\b|addEventListener\(\s*["\x27]navigate["\x27]|\.intercept\(\s*\{')
rows = json.load(open(sys.argv[1]))
pages = collections.defaultdict(set)
bodies = collections.defaultdict(set)
for r in rows:
    toks = set()
    for s in r['snippets']:
        for m in TOK.finditer(s):
            toks.add(re.sub(r'\s+', '', m.group(0)).replace("'", '"'))
    for t in toks:
        pages[t].add((r['client'], r['page']))
        bodies[t].add(r['body_fp'])
for t in sorted(pages, key=lambda t: -len(pages[t])):
    print(f'{len(pages[t]):6} pages {len(bodies[t]):6} bodies  {t}')
