"""Run bfcache_log.py on pages in setups B and C (4 at a time) and record, per departure from a
web page, Firefox's logged bfcache blocking reasons. Usage: bfcache_scan.py <urls.txt> <plan outdir> <out.jsonl>"""
import concurrent.futures, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bfcache_log import reasons
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import navqa
urls = [l.split()[0] for l in open(sys.argv[1]) if l.strip()]
plans, out = sys.argv[2], sys.argv[3]


def one(job):
    setup, url = job
    log = tempfile.mktemp(prefix=f'bf-{setup}-', suffix='.log', dir='/tmp/navqa-dbg')
    try:
        subprocess.run([sys.executable, '-I', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bfcache_log.py'), setup, url, plans, log],
                       capture_output=True, text=True, timeout=240)
        deps = [(navqa.scrub(u), r, b) for u, r, b in reasons(log) if u.startswith('http')]
    except Exception as e:
        deps = [('error', [str(e)[:100]], None)]
    finally:
        if os.path.exists(log):
            os.remove(log)
    return {'page': navqa.scrub(url), 'setup': setup, 'departures': deps}


with concurrent.futures.ThreadPoolExecutor(4) as ex, open(out, 'a') as fo:
    for r in ex.map(one, [(s, u) for u in urls for s in ('B', 'C')]):
        fo.write(json.dumps(r) + '\n'); fo.flush()
        print(r['setup'], r['page'][:60], [(d[2], d[1][:3]) for d in r['departures'][:3]], flush=True)
