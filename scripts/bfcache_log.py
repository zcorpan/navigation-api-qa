"""Visit a page in Firefox Nightly (setup B or C) with bfcache logging and print the logged
reasons for not keeping documents in bfcache. Usage: bfcache_log.py <setup> <url> <plan outdir> <logfile>"""
import hashlib, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import navqa
from selenium import webdriver
def main():
    setup, url, plans, log = sys.argv[1:5]
    orig_caps = webdriver.FirefoxOptions.to_capabilities
    def caps(self):
        c = orig_caps(self)
        c['moz:firefoxOptions'].setdefault('env', {}).update({'MOZ_LOG': 'SHIPBFCache:5,PageCache:5'})
        return c
    os.environ['MOZ_LOG'] = 'SHIPBFCache:5,PageCache:5'
    pid = hashlib.sha1(url.encode()).hexdigest()[:10]
    plan = json.load(open(f'{plans}/{pid}.json')).get('plan', {}) if os.path.exists(f'{plans}/{pid}.json') else {}
    orig_service = webdriver.FirefoxService
    webdriver.FirefoxService = lambda **kw: orig_service(service_args=['--allow-system-access'], log_output=log)
    be = navqa.Firefox(setup, trace=False)
    webdriver.FirefoxService = orig_service
    try:
        be.goto(url); navqa.settle(be, min_wait=3); be.call(navqa.CONSENT_JS)
        href = be.call(navqa.PICK_JS, ['link', plan.get('link')])
        print('link', href)
        if href:
            be.click(); navqa.settle(be)
            be.back(); navqa.settle(be)
            print('after back', be.call("() => [location.href, performance.getEntriesByType('navigation')[0].type]"))
            be.forward(); navqa.settle(be)
    finally:
        be.quit()


def reasons(logfile):
    """Per departure checked by the parent: (url, [reasons], blocked)."""
    out, cur = [], None
    for line in open(logfile, errors='replace'):
        line = re.sub(r'^\[[^]]*\]: ', '', line.rstrip())
        m = re.search(r'SHIPBFCache Checking (\S+)', line)
        if m:
            cur = [m.group(1), [], None]; continue
        if cur and re.search(r'SHIPBFCache\s+\*\s', line) and '** Blocked for document' not in line:
            cur[1].append(line.split('SHIPBFCache', 1)[1].strip(' *'))
        if cur and '+>' in line:
            cur[2] = 'should be blocked' in line; out.append(tuple(cur)); cur = None
    return out



if __name__ == '__main__':
    main()
