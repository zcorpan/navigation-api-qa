() => {
  if (window.__navqaInstalled) return;
  window.__navqaInstalled = true;
  const log = (window.__navqaLog = []);
  const counts = (window.__navqaCounts = {});
  const T0 = performance.now();
  const push = o => {
    if (window.__navqaInternal) return;
    o.t = Math.round(performance.now() - T0);
    const key = o.k + (o.m ? ':' + o.m : '') + (o.info ? ':' + o.info : '');
    counts[key] = (counts[key] || 0) + 1;
    if (counts[key] <= 25 && log.length < 500) log.push(o);
  };
  const str = (v, n = 160) => {
    try {
      return (typeof v === 'string' ? v : JSON.stringify(v) ?? String(v)).slice(0, n);
    } catch (e) {
      return '[unserializable]';
    }
  };
  const err = e => (e && e.name ? e.name + ': ' + e.message : String(e)).slice(0, 300);
  const stack = () => {
    try {
      return (new Error().stack || '').split('\n').filter(s => s && !s.includes('__navqa')).slice(1, 5).map(s => s.trim().slice(0, 240));
    } catch (e) {
      return [];
    }
  };
  addEventListener('error', e => { if (e instanceof ErrorEvent) push({ k: 'error', e: String(e.message).slice(0, 300), f: e.filename ? String(e.filename).slice(0, 200) : undefined, l: e.lineno }); }, true);
  addEventListener('unhandledrejection', e => push({ k: 'rejection', e: err(e.reason) }));
  addEventListener('popstate', e => push({ k: 'popstate', state: typeof e.state, url: location.href }), true);
  addEventListener('hashchange', () => push({ k: 'hashchange', url: location.href }), true);
  addEventListener('pageshow', e => push({ k: 'pageshow', persisted: e.persisted }), true);
  addEventListener('pagehide', () => {
    try { sessionStorage.setItem('__navqaPrev', JSON.stringify({ url: location.href, log: log.slice(-200), counts })); } catch (e) {}
  }, true);
  for (const m of ['pushState', 'replaceState']) {
    const orig = History.prototype[m];
    History.prototype[m] = function (...a) {
      push({ k: 'history', m, url: a[2] == null ? undefined : str(String(a[2]), 200) });
      return orig.apply(this, a);
    };
  }
  const n = window.navigation;
  if (!n || !window.Navigation) { push({ k: 'no-navigation' }); return; }
  const N = Navigation.prototype;
  const AEL = EventTarget.prototype.addEventListener;
  for (const m of ['navigate', 'reload', 'traverseTo', 'back', 'forward', 'updateCurrentEntry', 'entries']) {
    const orig = N[m];
    if (typeof orig !== 'function') continue;
    N[m] = function (...a) {
      const rec = { k: 'call', m, a: m === 'entries' ? undefined : str(a), s: stack() };
      push(rec);
      let r;
      try {
        r = orig.apply(this, a);
      } catch (e) {
        rec.threw = err(e);
        throw e;
      }
      if (m === 'entries') rec.len = r.length;
      if (r && r.committed && r.finished) {
        r.committed.then(() => push({ k: 'committed', m }), e => push({ k: 'committed-reject', m, e: err(e) }));
        r.finished.then(() => push({ k: 'finished', m }), e => push({ k: 'finished-reject', m, e: err(e) }));
      }
      return r;
    };
  }
  N.addEventListener = function (type, fn, o) {
    push({ k: 'listen', m: String(type), s: stack() });
    return AEL.call(this, type, fn, o);
  };
  for (const t of ['onnavigate', 'onnavigatesuccess', 'onnavigateerror', 'oncurrententrychange']) {
    const d = Object.getOwnPropertyDescriptor(N, t);
    if (d && d.set) Object.defineProperty(N, t, { ...d, set(v) { push({ k: 'listen', m: t, s: stack() }); return d.set.call(this, v); } });
  }
  for (const g of ['currentEntry', 'transition', 'activation', 'canGoBack', 'canGoForward']) {
    const d = Object.getOwnPropertyDescriptor(N, g);
    if (d && d.get) Object.defineProperty(N, g, { ...d, get() { if (!window.__navqaInternal) push({ k: 'get', m: g }); return d.get.call(this); } });
  }
  const NE = window.NavigateEvent && NavigateEvent.prototype;
  if (NE) {
    for (const m of ['intercept', 'scroll']) {
      const orig = NE[m];
      if (typeof orig !== 'function') continue;
      NE[m] = function (o) {
        const rec = { k: m, m: this.navigationType, url: this.destination && str(this.destination.url, 200), s: stack() };
        if (o && m === 'intercept') rec.opts = { handler: typeof o.handler, precommit: typeof o.precommitHandler, focusReset: o.focusReset, scroll: o.scroll };
        push(rec);
        try {
          return orig.call(this, o);
        } catch (e) {
          rec.threw = err(e);
          throw e;
        }
      };
    }
  }
  AEL.call(n, 'navigate', e => {
    const rec = {
      k: 'navigate', m: e.navigationType, url: str(e.destination.url, 200), same: e.destination.sameDocument,
      canIntercept: e.canIntercept, userInitiated: e.userInitiated, hashChange: e.hashChange, cancelable: e.cancelable,
      form: !!e.formData, download: e.downloadRequest, info: e.info === undefined ? undefined : str(e.info, 40),
      src: e.sourceElement ? e.sourceElement.tagName : null,
    };
    push(rec);
    setTimeout(() => { rec.prevented = e.defaultPrevented; }, 0);
  });
  AEL.call(n, 'navigatesuccess', () => push({ k: 'navigatesuccess' }));
  AEL.call(n, 'navigateerror', e => push({ k: 'navigateerror', e: err(e.error) }));
  AEL.call(n, 'currententrychange', e => push({ k: 'currententrychange', m: e.navigationType, from: e.from && str(e.from.url, 200) }));
}
