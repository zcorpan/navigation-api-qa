"""Re-scrub run records in place: long tokens, the tester's publish terms, IP-like hostnames.
Usage: scrub_out.py <dir> ..."""
import glob, json, os, re, sys
terms = [t for t in open('.publish-terms').read().splitlines() if len(t) > 2] if os.path.exists('.publish-terms') else []
TOKEN = re.compile(r'(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{200,}={0,2}')
IPHOST = re.compile(r'\b\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\b')
TERMS = re.compile('|'.join(re.escape(t) for t in terms), re.I) if terms else None


def scrub(s):
    s = TOKEN.sub('<token>', s)
    s = IPHOST.sub('<ip>', s)
    return TERMS.sub('<term>', s) if TERMS else s


def walk(v):
    if isinstance(v, str):
        return scrub(v)
    if isinstance(v, list):
        return [walk(x) for x in v]
    if isinstance(v, dict):
        return {k: walk(x) for k, x in v.items()}
    return v


n = 0
for d in sys.argv[1:]:
    for f in glob.glob(os.path.join(d, '**', '*.json*'), recursive=True):
        if '/text/' in f or f.endswith('.gz'):
            continue
        if f.endswith('.jsonl'):
            lines = [json.dumps(walk(json.loads(l))) for l in open(f) if l.strip()]
            new = '\n'.join(lines) + '\n'
        else:
            new = json.dumps(walk(json.load(open(f))), indent=1)
        if new != open(f).read():
            open(f, 'w').write(new); n += 1
print(n, 'files rewritten')
