"""Pages to recheck: Firefox diffs C doesn't share, on navigation metrics, plus Safari diffs on them.
Usage: recheck_list.py <outdir> <out.txt>"""
import json, os, sys
NAV = {'path', 'sameDoc', 'histDelta', 'navLen', 'navIdx', 'intercepted', 'stuck', 'scrollY', 'navErrors', 'transition'}
flags = json.load(open(os.path.join(sys.argv[1], 'flags.json')))
out = []
for f in flags:
    why = sorted({f"{d['setup']}:{d['step']}:{d['metric']}" for d in f['diffs']
                  if d['metric'] in NAV and ((d['setup'] == 'B' and d.get('C_same_as_A')) or d['setup'] == 'D')})
    if why:
        out.append(f"{f['page']} {','.join(why)}")
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
print(len(out), 'pages')
