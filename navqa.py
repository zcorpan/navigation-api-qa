"""Navigation API QA harness.

Setups: A, A2 = Chrome Canary; B = Firefox Nightly; C = Firefox Nightly with the Navigation API off;
D = Safari Technology Preview.

  navqa.py run <setup> <pages.txt> <outdir> [--workers N] [--plan-from <outdir of A>]
  navqa.py worker <setup> <outdir>        (internal: reads "id url plan_json" lines on stdin)

Each page: load, then click a same-origin link, back, forward, reload, click a fragment link, back.
Per step the record has location and Navigation API state, whether the step stayed in the same
document, the trace log from trace.js, console errors, and a viewport screenshot.
"""
import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = open(os.path.join(HERE, 'trace.js')).read().strip()
CANARY = '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'
NIGHTLY = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
STP_DRIVER = '/Applications/Safari Technology Preview.app/Contents/MacOS/safaridriver'
W, H = 1280, 800
VISIT_TIMEOUT = 240
REDO_ERRORS = '--redo-errors' in sys.argv

URL_QUERY = re.compile(r'([a-z][a-z0-9+.-]*://[^\s?#"\'<>]+)[?#][^\s"\'<>]*', re.I)
CC_HOST = re.compile(r'\b(google|bing|yahoo|amazon|facebook)\.(?:co\.)?(?!com\b|net\b|org\b)[a-z]{2}\b')
IP = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')


TOKEN = re.compile(r'[A-Za-z0-9+/_-]{60,}={0,2}')
IPHOST = re.compile(r'\b\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\b')


def scrub(s):
    if not isinstance(s, str):
        return s
    s = IP.sub('<ip>', CC_HOST.sub(r'\1.<cc>', URL_QUERY.sub(r'\1', s)))
    return IPHOST.sub('<ip>', TOKEN.sub('<token>', s))


def scrub_deep(v):
    if isinstance(v, str):
        return scrub(v)
    if isinstance(v, list):
        return [scrub_deep(x) for x in v]
    if isinstance(v, dict):
        return {k: scrub_deep(x) for k, x in v.items()}
    return v


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12] if isinstance(s, str) else None


STATE_JS = r"""() => {
  window.__navqaInternal = true;
  try {
    const n = window.navigation;
    let nav = null;
    if (n && n.entries) {
      try {
        const ce = n.currentEntry;
        nav = { len: n.entries().length, idx: ce ? ce.index : null, url: ce ? ce.url : null, key: ce ? ce.key : null,
                sameDoc: ce ? ce.sameDocument : null, canGoBack: n.canGoBack, canGoForward: n.canGoForward,
                transition: n.transition ? { type: n.transition.navigationType, from: n.transition.from && n.transition.from.url } : null,
                activation: n.activation && self.origin !== 'null' ? { type: n.activation.navigationType, entry: n.activation.entry && n.activation.entry.url,
                  from: n.activation.from && n.activation.from.url, entryIsCurrent: !!(ce && n.activation.entry && n.activation.entry.key === ce.key) } : null };
      } catch (e) { nav = { error: String(e) }; }
    }
    let prev = null;
    try { prev = sessionStorage.getItem('__navqaPrev'); if (prev) sessionStorage.removeItem('__navqaPrev'); } catch (e) {}
    const a = document.activeElement;
    let hs;
    try { hs = history.state === null ? 'null' : typeof history.state; } catch (e) { hs = 'error'; }
    const text = document.body ? document.body.innerText || '' : '';
    return {
      url: location.href, title: document.title, readyState: document.readyState, timeOrigin: performance.timeOrigin,
      marker: window.__navqaMarker || null, histLen: history.length, histState: hs,
      scrollX: Math.round(scrollX), scrollY: Math.round(scrollY), docH: document.documentElement ? document.documentElement.scrollHeight : 0,
      active: a ? a.tagName + (a.id ? '#' + a.id : '') : null, textLen: text.length, text: text.slice(0, 2000),
      nav, log: window.__navqaLog || null, counts: window.__navqaCounts || null, prev: prev ? JSON.parse(prev) : null,
    };
  } finally { window.__navqaInternal = false; }
}"""

PICK_JS = r"""([kind, pref]) => {
  document.querySelectorAll('[data-navqa-pick]').forEach(e => e.removeAttribute('data-navqa-pick'));
  const vis = a => {
    const r = a.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return false;
    const s = getComputedStyle(a);
    if (s.visibility !== 'visible' || +s.opacity < 0.1) return false;
    const x = Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1), y = Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 1);
    const el = document.elementFromPoint(x, y);
    return !!el && (el === a || a.contains(el));
  };
  const ok = a => {
    let u;
    try { u = new URL(a.href, location.href); } catch (e) { return false; }
    if (!/^https?:$/.test(u.protocol) || u.origin !== location.origin) return false;
    if (a.target && a.target !== '_self') return false;
    if (a.hasAttribute('download')) return false;
    const samePath = u.pathname === location.pathname && u.search === location.search;
    if (kind === 'link') {
      if (samePath) return false;
      if (/(log-?in|sign-?in|log-?out|sign-?out|cart|basket|checkout|account|register|sign-?up|subscribe|password|auth|oauth|delete|unsubscribe)/i.test(u.pathname + u.search)) return false;
      if (/\.(pdf|zip|jpe?g|png|gif|webp|mp4|mp3|apk|exe|dmg)$/i.test(u.pathname)) return false;
      return true;
    }
    if (!samePath || !u.hash || u.hash === '#') return false;
    const id = decodeURIComponent(u.hash.slice(1));
    return !!(document.getElementById(id) || document.getElementsByName(id).length);
  };
  const all = [...document.querySelectorAll('a[href]')].filter(ok);
  const shown = a => { const r = a.getBoundingClientRect(), s = getComputedStyle(a); return r.width >= 4 && r.height >= 4 && s.visibility === 'visible' && +s.opacity >= 0.1; };
  const reach = a => { a.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }); return vis(a); };
  let a = pref && (all.find(l => l.href === pref && vis(l)) || all.find(l => l.href === pref && shown(l) && reach(l)));
  if (!a) a = all.find(vis);
  if (!a) { for (const l of all.filter(shown).slice(0, 40)) if (reach(l)) { a = l; break; } }
  if (!a) return null;
  if (!window.__navqaClickHook) {
    window.__navqaClickHook = true;
    document.addEventListener('click', e => { if (e.target && e.target.closest && e.target.closest('[data-navqa-pick]')) window.__navqaClicked = true; }, true);
  }
  window.__navqaClicked = false;
  a.setAttribute('data-navqa-pick', '1');
  return a.href;
}"""

CONSENT_JS = r"""() => {
  const sels = ['#onetrust-accept-btn-handler', '#didomi-notice-agree-button', '.fc-cta-consent', '#L2AGLb', '[data-testid="uc-accept-all-button"]',
    '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', '#CybotCookiebotDialogBodyButtonAccept', '.cky-btn-accept', '#truste-consent-button',
    '.qc-cmp2-summary-buttons button[mode="primary"]', 'button[data-cookiebanner="accept_button"]', '#accept-recommended-btn-handler', '.osano-cm-accept-all',
    '#cookie-accept', '.cc-allow', '.cmplz-accept', '#wt-cli-accept-all-btn', 'button.iubenda-cs-accept-btn', '.evidon-banner-acceptbutton'];
  for (const s of sels) { const b = document.querySelector(s); if (b && b.getBoundingClientRect().width > 0) { b.click(); return s; } }
  const words = /^\s*(accept( all)?( cookies)?|agree|i agree|allow( all)?|got it|ok|okay|aceptar( todo| todas)?|acepto|aceitar( todos)?|accetta( tutto)?|accepter( tout)?|tout accepter|j'accepte|akzeptieren|alle akzeptieren|zustimmen|alle zulassen|elfogadom|összes elfogadása|kabul et|tümünü kabul et|zgadzam się|akceptuję|souhlasím|prijať všetko|accepteren|alles accepteren|godta alle|acceptera alla|hyväksy kaikki|accept și închide|同意|同意する|모두 동의|принять|согласен)\s*$/i;
  for (const b of document.querySelectorAll('button, a[role="button"], [role="button"], input[type="button"], input[type="submit"]')) {
    const t = (b.innerText || b.value || '').trim();
    if (t.length < 40 && words.test(t)) {
      let p = b, hit = false;
      for (let i = 0; p && i < 8; i++, p = p.parentElement) if (/consent|cookie|cmp|gdpr|privacy|banner|notice/i.test((p.id || '') + ' ' + (typeof p.className === 'string' ? p.className : ''))) { hit = true; break; }
      const r = b.getBoundingClientRect();
      if (hit && r.width > 0 && r.height > 0) { b.click(); return 'text:' + t.slice(0, 20); }
    }
  }
  return null;
}"""

SETTLE_JS = "() => { window.__navqaInternal = true; try { return [location.href, document.readyState, !!(window.navigation && navigation.transition), performance.timeOrigin]; } finally { window.__navqaInternal = false; } }"


class Chrome:
    def __init__(self, setup, trace=True):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(executable_path=CANARY, headless=False,
                                               args=[f'--window-size={W},{H + 140}', '--no-first-run', '--no-default-browser-check'])
        self.ctx = self.browser.new_context(viewport={'width': W, 'height': H}, ignore_https_errors=True)
        if trace:
            self.ctx.add_init_script(script=f'({TRACE})()')
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append({'k': 'pageerror', 'e': str(e)[:300]}))
        self.page.on('console', lambda m: m.type in ('error', 'warning') and self.errors.append({'k': 'console-' + m.type, 'e': m.text[:300]}))
        self.page.on('dialog', lambda d: d.dismiss())
        self.page.set_default_timeout(15000)

    def version(self):
        return 'Chrome Canary ' + self.browser.version

    def call(self, fn, arg=None):
        return self.page.evaluate(fn, arg)

    def goto(self, url):
        try:
            self.page.goto(url, wait_until='load', timeout=45000)
        except Exception as e:
            if 'Timeout' not in str(e):
                raise

    def click(self):
        try:
            self.page.click('[data-navqa-pick]', timeout=5000, no_wait_after=True)
            return 'native'
        except Exception:
            self.page.evaluate("() => document.querySelector('[data-navqa-pick]').click()")
            return 'js'

    def back(self):
        try:
            self.page.go_back(wait_until='commit', timeout=15000)
        except Exception:
            pass

    def forward(self):
        try:
            self.page.go_forward(wait_until='commit', timeout=15000)
        except Exception:
            pass

    def reload(self):
        try:
            self.page.reload(wait_until='load', timeout=30000)
        except Exception:
            pass

    def shot(self, path):
        self.page.screenshot(path=path, timeout=15000)

    def inject(self):
        pass

    def reset(self):
        self.page.goto('about:blank')
        self.ctx.clear_cookies()

    def quit(self):
        try:
            self.browser.close()
            self.pw.stop()
        except Exception:
            pass


class Selenium:
    preload = False

    def call(self, fn, arg=None):
        return self.d.execute_script(f'return ({fn})(arguments[0])', arg)

    def goto(self, url):
        from selenium.common.exceptions import TimeoutException
        try:
            self.d.get(url)
        except TimeoutException:
            pass

    def click(self):
        from selenium.webdriver.common.by import By
        el = self.d.find_element(By.CSS_SELECTOR, '[data-navqa-pick]')
        try:
            el.click()
            return 'native'
        except Exception:
            self.d.execute_script("document.querySelector('[data-navqa-pick]').click()")
            return 'js'

    def _nav(self, f):
        from selenium.common.exceptions import TimeoutException
        try:
            f()
        except TimeoutException:
            pass

    def back(self):
        self._nav(self.d.back)

    def forward(self):
        self._nav(self.d.forward)

    def reload(self):
        self._nav(self.d.refresh)

    def shot(self, path):
        self.d.save_screenshot(path)

    def inject(self):
        if self.trace and not self.preload:
            self.d.execute_script(f'({TRACE})()')

    def reset(self):
        self.d.get('about:blank')
        self.d.delete_all_cookies()

    def quit(self):
        try:
            self.d.quit()
        except Exception:
            pass


class Firefox(Selenium):
    preload = True

    def __init__(self, setup, trace=True):
        self.trace = trace
        from selenium import webdriver
        o = webdriver.FirefoxOptions()
        o.binary_location = NIGHTLY
        o.add_argument('-headless')
        o.enable_bidi = True
        o.set_preference('dom.navigation.webidl.enabled', setup != 'C')
        o.set_preference('browser.shell.checkDefaultBrowser', False)
        o.set_preference('datareporting.policy.dataSubmissionEnabled', False)
        o.set_preference('dom.disable_beforeunload', True)
        self.d = webdriver.Firefox(options=o, service=webdriver.FirefoxService(service_args=['--allow-system-access']))
        self.d.set_window_rect(0, 0, W, H)
        inner = self.d.execute_script('return [innerWidth, innerHeight]')
        self.d.set_window_rect(0, 0, W + (W - inner[0]), H + (H - inner[1]))
        self.d.set_page_load_timeout(45)
        self.d.set_script_timeout(15)
        if trace:
            self.d.script.pin(TRACE)
        self.errors = []
        self.d.script.add_javascript_error_handler(lambda e: self.errors.append({'k': 'pageerror', 'e': str(getattr(e, 'text', e))[:300]}))
        self.d.script.add_console_message_handler(
            lambda m: getattr(m, 'level', '') in ('error', 'warn') and self.errors.append({'k': 'console-' + m.level, 'e': str(getattr(m, 'text', m))[:300]}))
        self.v = self.d.capabilities.get('browserVersion')

    def version(self):
        return 'Firefox Nightly ' + str(self.v)

    def uiback(self):
        with self.d.context(self.d.CONTEXT_CHROME):
            self.d.execute_script('gBrowser.goBack()')


class Safari(Selenium):
    def __init__(self, setup, trace=True):
        self.trace = trace
        from selenium import webdriver
        o = webdriver.SafariOptions()
        o.use_technology_preview = True
        self.d = webdriver.Safari(options=o, service=webdriver.SafariService(executable_path=STP_DRIVER))
        self.d.set_window_rect(0, 0, W, H)
        inner = self.d.execute_script('return [innerWidth, innerHeight]')
        self.d.set_window_rect(0, 0, W + (W - inner[0]), H + (H - inner[1]))
        self.d.set_page_load_timeout(45)
        self.d.set_script_timeout(15)
        self.errors = []
        self.v = self.d.capabilities.get('browserVersion')

    def version(self):
        return 'Safari TP ' + str(self.v)

    def back(self):
        # After script clicks, safaridriver's back skips every entry added without a user gesture;
        # Chrome's CDP back and Firefox's WebDriver back aren't browser UI traversals either.
        self.d.execute_script('history.back()')

    def forward(self):
        self.d.execute_script('history.forward()')

    def click(self):
        # safaridriver's element click often never reaches the page on real sites (no click event
        # is dispatched), so Safari visits use a script click.
        self.d.execute_script("document.querySelector('[data-navqa-pick]').click()")
        return 'js'


BACKENDS = {'A': Chrome, 'A2': Chrome, 'B': Firefox, 'C': Firefox, 'D': Safari}


def settle(be, min_wait=1.5, max_wait=12):
    t0 = time.time()
    time.sleep(min_wait)
    last, since = None, None
    while time.time() - t0 < max_wait:
        try:
            s = be.call(SETTLE_JS)
        except Exception:
            s = None
        if s and s[1] == 'complete' and not s[2]:
            if s == last:
                if time.time() - since >= 1.0:
                    return round(time.time() - t0, 1)
            else:
                last, since = s, time.time()
        else:
            last = None
        time.sleep(0.25)
    return None


def state(be, marker):
    for _ in range(4):
        try:
            be.inject()
            s = be.call(STATE_JS)
            if isinstance(s, dict):
                break
            s = {'error': f'state returned {type(s).__name__}'}
        except Exception as e:
            s = {'error': str(e)[:300]}
        time.sleep(1)
    s['sameDoc'] = s.get('marker') == marker if 'error' not in s else None
    s['errors'], be.errors[:] = list(be.errors), []
    return s


STEPS = [('load', None), ('link', 'link'), ('link2', 'link'), ('back', None), ('back3', None), ('forward', None), ('reload', None),
         ('fragment', 'fragment'), ('back2', None)]
if os.environ.get('NAVQA_STEPS') == 'v1':
    STEPS = [s for s in STEPS if s[0] not in ('link2', 'back3')]


def visit(be, pid, url, plan, shotdir):
    rec = {'id': pid, 'page': url, 'steps': [], 'plan': {}}
    t0 = time.time()
    be.goto(url)
    settle(be, min_wait=3)
    try:
        rec['consent'] = be.call(CONSENT_JS)
        if rec['consent']:
            settle(be, min_wait=1.5)
    except Exception as e:
        rec['consentError'] = str(e)[:200]
    steps = STEPS
    marker = None
    needs = {'link2': 'link', 'back': 'link', 'back3': 'link2', 'forward': 'back', 'reload': 'load', 'back2': 'fragment'}
    done = {'load'}
    for i, (name, pick) in enumerate(steps):
        info = {'step': name}
        if name in needs and needs[name] not in done:
            info['skipped'] = True
            rec['steps'].append(info)
            continue
        if name != 'load':
            if pick:
                try:
                    if be.call(CONSENT_JS):
                        rec['consentLate'] = rec.get('consentLate', 0) + 1
                        settle(be, min_wait=1)
                except Exception:
                    pass
                try:
                    href = be.call(PICK_JS, [pick, (plan or {}).get(name)])
                except Exception as e:
                    href = None
                    info['pickError'] = str(e)[:200]
                info['href'] = href
                rec['plan'][name] = href
                if not href and name == 'fragment':
                    try:
                        be.call("() => { location.hash = 'navqa-frag'; }")
                        info['href'] = rec['plan'][name] = href = '#navqa-frag'
                        info['click'] = 'script-hash'
                    except Exception as e:
                        info['clickError'] = str(e)[:200]
                elif not href:
                    info['skipped'] = True
                    rec['steps'].append(info)
                    continue
                else:
                    try:
                        info['click'] = be.click()
                    except Exception as e:
                        info['clickError'] = str(e)[:200]
            elif name in ('back', 'back2', 'back3'):
                be.back()
            elif name == 'forward':
                be.forward()
            elif name == 'reload':
                be.reload()
            info['settle'] = settle(be)
        done.add(name)
        info.update(state(be, marker))
        marker = f'm{i}'
        try:
            be.call(f"() => {{ window.__navqaMarker = '{marker}'; }}")
        except Exception:
            pass
        try:
            be.shot(os.path.join(shotdir, f'{pid}-{name}.png'))
        except Exception as e:
            info['shotError'] = str(e)[:200]
        rec['steps'].append(info)
    rec['elapsed'] = round(time.time() - t0, 1)
    return rec


def finish(rec):
    """Move page text to a separate local-only record, hash URLs, scrub the rest."""
    text = {}
    for s in rec.get('steps', []):
        text[s['step']] = {'text': s.pop('text', None), 'title': s.get('title'), 'url': s.get('url')}
        for k in ('url', 'title'):
            if k in s:
                s[k + 'Hash'] = h(s[k])
        if s.get('nav') and isinstance(s['nav'], dict):
            s['nav']['urlHash'] = h(s['nav'].get('url'))
        s.pop('title', None)
    return scrub_deep(rec), text


def worker(setup, outdir):
    shotdir = os.path.join(outdir, 'shots')
    os.makedirs(shotdir, exist_ok=True)
    os.makedirs(os.path.join(outdir, 'text'), exist_ok=True)
    be, n = None, 0
    for line in sys.stdin:
        pid, url, plan = line.rstrip('\n').split(' ', 2)
        plan = json.loads(plan)
        try:
            if be is None or n >= 12:
                if be:
                    be.quit()
                be, n = BACKENDS[setup](setup), 0
            else:
                be.reset()
            n += 1
            rec = visit(be, pid, url, plan, shotdir)
            rec['browser'] = be.version()
        except Exception as e:
            rec = {'id': pid, 'page': url, 'error': f'{type(e).__name__}: {str(e)[:400]}'}
            if be:
                be.quit()
            be = None
        rec['setup'] = setup
        rec, text = finish(rec)
        json.dump(rec, open(os.path.join(outdir, pid + '.json'), 'w'), indent=1)
        json.dump(text, open(os.path.join(outdir, 'text', pid + '.json'), 'w'))
        print('done', pid, flush=True)
    if be:
        be.quit()


def pid_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:10]


def run(setup, pages_file, outdir, workers, plan_from):
    os.makedirs(outdir, exist_ok=True)
    urls = [l.split()[0] for l in open(pages_file) if l.strip() and not l.startswith('#')]
    def needed(u):
        f = os.path.join(outdir, pid_of(u) + '.json')
        return not os.path.exists(f) or (REDO_ERRORS and 'error' in json.load(open(f)))
    todo = [u for u in urls if needed(u)]
    if setup == 'D':
        workers = 1
    print(f'{setup}: {len(todo)} of {len(urls)} pages to visit with {workers} workers', flush=True)
    lock = threading.Lock()

    def plan_for(u):
        if plan_from:
            p = os.path.join(plan_from, pid_of(u) + '.json')
            if os.path.exists(p):
                return json.load(open(p)).get('plan') or {}
        return {}

    def spawn():
        return subprocess.Popen([sys.executable, '-I', os.path.abspath(__file__), 'worker', setup, outdir], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, start_new_session=True, cwd=HERE)

    def lane():
        p = spawn()
        while True:
            with lock:
                if not todo:
                    break
                u = todo.pop(0)
            pid = pid_of(u)
            p.stdin.write(f'{pid} {u} {json.dumps(plan_for(u))}\n')
            p.stdin.flush()
            sel = selectors.DefaultSelector()
            sel.register(p.stdout, selectors.EVENT_READ)
            deadline = time.time() + VISIT_TIMEOUT
            ok = False
            while time.time() < deadline:
                if sel.select(timeout=5):
                    line = p.stdout.readline()
                    if not line:
                        break
                    if line.startswith('done ' + pid):
                        ok = True
                        break
            sel.close()
            if not ok:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except Exception:
                    pass
                if setup == 'D':
                    subprocess.run(['pkill', '-f', 'Safari Technology Preview.app/Contents/MacOS/Safari Technology Preview'], check=False)
                    time.sleep(3)
                rec = {'id': pid, 'page': scrub(u), 'setup': setup, 'error': f'visit timed out after {VISIT_TIMEOUT}s'}
                json.dump(rec, open(os.path.join(outdir, pid + '.json'), 'w'), indent=1)
                p = spawn()
            print(setup, 'ok' if ok else 'TIMEOUT', pid, u[:80], flush=True)
        try:
            p.stdin.close()
            p.wait(timeout=60)
        except Exception:
            os.killpg(p.pid, signal.SIGKILL)

    threads = [threading.Thread(target=lane) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == '__main__':
    if sys.argv[1] == 'worker':
        worker(sys.argv[2], sys.argv[3])
    else:
        args = sys.argv[2:]
        workers = int(args[args.index('--workers') + 1]) if '--workers' in args else 3
        plan_from = args[args.index('--plan-from') + 1] if '--plan-from' in args else None
        run(args[0], args[1], args[2], workers, plan_from)
