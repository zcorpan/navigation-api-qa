"""WebDriver Element Click on a non-navigating button leaves an unload listener on the page, so a
later navigation away can't put the page in bfcache. Run with python3 server.py serving the repo.
Prints Firefox's bfcache decision (from MOZ_LOG=SHIPBFCache:5) for the page, without and with the
click; with W3C pointer actions instead of Element Click there's no listener."""
import os, re, sys, time
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

os.environ['MOZ_LOG'] = 'SHIPBFCache:5'
URL = 'http://127.0.0.1:8765/findings/infra-04-marionette-click-unload-listener/test.html'
for mode in ('none', 'element-click', 'actions'):
    log = f'/tmp/infra04-{mode}.log'
    o = webdriver.FirefoxOptions(); o.binary_location = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'; o.add_argument('-headless')
    d = webdriver.Firefox(options=o, service=webdriver.FirefoxService(log_output=log))
    try:
        d.get(URL); time.sleep(1)
        if mode == 'element-click':
            d.find_element(By.ID, 'b').click()
        elif mode == 'actions':
            ActionChains(d).move_to_element(d.find_element(By.ID, 'b')).click().perform()
        time.sleep(1)
        d.execute_script("setTimeout(() => { location.href = 'page2.html'; }, 300)"); time.sleep(2)
        d.back(); time.sleep(1.5)
    finally:
        d.quit()
    txt = open(log, errors='replace').read()
    m = re.search(r'Checking (\S+test\.html)\n(.*?)\+> \S+ (should(?:n\'t)? be blocked)', txt, re.S)
    print(mode, '->', m.group(3) if m else 'no decision logged', re.findall(r'\* (unload listener|requests in the loadgroup)', m.group(2)) if m else '')
