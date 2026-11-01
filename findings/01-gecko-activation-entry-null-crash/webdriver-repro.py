import sys, time
from selenium import webdriver
first = sys.argv[1]; read = sys.argv[2]
o = webdriver.FirefoxOptions(); o.binary_location = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'; o.add_argument('-headless')
d = webdriver.Firefox(options=o)
try:
    d.get(first); d.get('http://127.0.0.1:8765/tests/plain.html'); time.sleep(1)
    d.back(); time.sleep(2)
    r = d.execute_script(read)
    time.sleep(4); d.execute_script("return 1")
    print(first, read[:40], 'ok', d.current_url, r)
except Exception as e:
    print(first, read[:40], 'CRASH' if 'marionette' in str(e) or 'session' in str(e).lower() else 'ERR', str(e)[:60])
finally:
    try: d.quit()
    except Exception: pass
