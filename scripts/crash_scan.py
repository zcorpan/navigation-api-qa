"""Visit each URL in its own fresh Firefox session (setup B or C) and report whether the browser
died (content crash with geckodriver's MOZ_CRASHREPORTER_SHUTDOWN) and after which step.
Usage: crash_scan.py <setup> <urls.txt> <out.jsonl> [plan outdir]"""
import json, os, sys, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import navqa
setup, urls, out = sys.argv[1], sys.argv[2], sys.argv[3]
plans = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs('/tmp/navqa-crashscan', exist_ok=True)
with open(out, 'a') as fo:
    for u in [l.split()[0] for l in open(urls) if l.strip()]:
        pid = hashlib.sha1(u.encode()).hexdigest()[:10]
        plan = {}
        if plans and os.path.exists(f'{plans}/{pid}.json'):
            plan = json.load(open(f'{plans}/{pid}.json')).get('plan') or {}
        res = {'page': navqa.scrub(u), 'setup': setup}
        try:
            be = navqa.BACKENDS[setup](setup)
            try:
                be.d.get('about:blank')
                r = navqa.visit(be, pid, u, plan, '/tmp/navqa-crashscan')
                dead = [s['step'] for s in r['steps'] if 'connection' in (s.get('error') or '') or 'session' in (s.get('error') or '').lower()]
                res['diedAt'] = dead[0] if dead else None
                if not dead:
                    try:
                        be.reset(); be.d.current_url
                    except Exception:
                        res['diedAt'] = 'reset'
            finally:
                be.quit()
        except Exception as e:
            res['diedAt'] = 'visit'; res['error'] = str(e)[:120]
        print(json.dumps(res), flush=True); fo.write(json.dumps(res) + '\n')
