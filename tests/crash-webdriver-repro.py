import sys, time; sys.path.insert(0, '/tmp/navigation-api-qa')
import navqa
v = sys.argv[1]
be = navqa.Firefox('B', trace=False); d = be.d
url = 'http://127.0.0.1:8765/tests/replace-hash-then-back.html' + '?' + 'step=2'
S = lambda: navqa.settle(be) if 'settle' in v else time.sleep(2)
R = lambda: (be.call(navqa.STATE_JS) if 'state' in v else None, be.call("() => { window.__navqaMarker = 'm'; }") if 'marker' in v else None)
try:
    d.get('about:blank'); be.goto(url); S(); R()
    be.reload(); S(); R()
    be.call("() => { location.hash = 'navqa-frag'; }"); S(); R()
    be.back(); S(); R()
    print(v, 'ok', d.current_url[-30:])
except Exception as e:
    print(v, 'CRASH', str(e)[:60])
finally:
    try: d.quit()
    except Exception: pass
