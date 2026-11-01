"""Run local test pages in Chrome Canary, Firefox Nightly (API on and off), and Safari TP.

Usage: testrun.py <tests/x.html> [...] [--setups A,B,C,D]

A test page sets window.__plan, an array of steps run after load: 'click <selector>' (native
click), 'jsclick <selector>', 'back', 'forward', 'reload', 'wait <ms>', 'key <selector> <text>'.
Results: window.__result, or sessionStorage.__result when the test ends in another document.
Writes tests/results/<test>.json and prints one line per browser.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import navqa  # noqa: E402

BASE = 'http://127.0.0.1:8765/'
RESULT_JS = r"""() => { try { const r = window.__result !== undefined ? window.__result : JSON.parse(sessionStorage.getItem('__result') || 'null'); return JSON.parse(JSON.stringify(r === undefined ? null : r)); } catch (e) { return {harnessError: String(e)}; } }"""


def click(be, sel, native=True):
    be.call("(s) => { document.querySelectorAll('[data-navqa-pick]').forEach(e => e.removeAttribute('data-navqa-pick')); document.querySelector(s).setAttribute('data-navqa-pick', '1'); }", sel)
    if native:
        return be.click()
    be.call("() => document.querySelector('[data-navqa-pick]').click()")


def run_test(be, path):
    url = BASE + path
    be.goto(url)
    time.sleep(0.5)
    plan = be.call('() => window.__plan || []')
    for step in plan:
        op, _, arg = step.partition(' ')
        try:
            if op == 'click':
                click(be, arg)
            elif op == 'jsclick':
                click(be, arg, native=False)
            elif op == 'back':
                be.back()
            elif op == 'uiback':
                be.uiback() if hasattr(be, 'uiback') else be.back()
            elif op == 'forward':
                be.forward()
            elif op == 'reload':
                be.reload()
            elif op == 'wait':
                time.sleep(int(arg) / 1000)
        except Exception as e:
            return {'harnessError': f'{step}: {e}'[:300]}
    for _ in range(40):
        r = be.call(RESULT_JS)
        if r is not None and not (isinstance(r, dict) and r.get('pending')):
            return r
        time.sleep(0.25)
    return {'harnessError': 'no result', 'partial': r}


def main():
    args = sys.argv[1:]
    setups = 'A,B,C,D'.split(',')
    if '--setups' in args:
        i = args.index('--setups')
        setups = args[i + 1].split(',')
        del args[i:i + 2]
    os.makedirs('tests/results', exist_ok=True)
    for path in args:
        rel = os.path.relpath(path, '.')
        out = {}
        for s in setups:
            be = navqa.BACKENDS[s](s, trace=False)
            try:
                out[s] = {'browser': be.version(), 'result': run_test(be, rel)}
            except Exception as e:
                out[s] = {'browser': be.version(), 'result': {'harnessError': str(e)[:300]}}
            finally:
                be.quit()
            print(f'{s:2} {out[s]["browser"]:28} {json.dumps(out[s]["result"])[:1500]}', flush=True)
        name = os.path.basename(path).replace('.html', '').replace('?', '-').replace('&', '-').replace('=', '')
        json.dump(out, open(os.path.join('tests/results', name + '.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
