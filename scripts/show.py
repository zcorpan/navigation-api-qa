"""Side-by-side per-step summary of one page across setups. Usage: show.py <outdir> <page-id or url substring> [setups]"""
import glob, json, os, sys, hashlib
out, key = sys.argv[1], sys.argv[2]
setups = (sys.argv[3] if len(sys.argv) > 3 else 'A,A2,B,C,D').split(',')
pid = key if len(key) == 10 and os.path.exists(f'{out}/A/{key}.json') else None
if not pid:
    for f in glob.glob(f'{out}/A/*.json'):
        if key in json.load(open(f))['page']:
            pid = os.path.basename(f)[:-5]; break
print(pid)
for s in setups:
    f = f'{out}/{s}/{pid}.json'
    if not os.path.exists(f):
        continue
    r = json.load(open(f))
    print(f'== {s} {r.get("browser")} {r.get("error", "")[:100]} consent={r.get("consent")}')
    seen = 0
    for st in r.get('steps', []):
        if st.get('skipped'):
            print(f'   {st["step"]:9} skipped'); continue
        log = st.get('log') or []
        ev = log[seen:] if st.get('sameDoc') else ((st.get('prev') or {}).get('log') or [])[-8:] + log
        seen = len(log)
        nav = st.get('nav') or {}
        evs = [e['k'] + (':' + str(e['m']) if e.get('m') else '') + (':P' if e.get('prevented') else '') + (':' + e['e'][:30] if e.get('e') else '') for e in ev if e['k'] not in ('get',)]
        print(f'   {st["step"]:9} {st.get("click") or "":7} same={str(st.get("sameDoc"))[:1]} url={(st.get("url") or "")[-50:]:50} hist={st.get("histLen")} nav={nav.get("len")}/{nav.get("idx")} y={st.get("scrollY")} settle={st.get("settle")}')
        if evs:
            print('             ', ' '.join(evs)[:400])
