# Navigation API QA: Firefox Nightly vs Chrome Canary and Safari TP on top-ranked pages

A live-page QA run of the Navigation API (`window.navigation`): top-ranked pages that use it,
loaded and driven in Firefox Nightly 161.0a1, Chrome Canary 159.0.8136.0 and Safari TP 255, plus
local test pages for patterns those pages contain. Findings are in [`findings/`](findings/), one
directory per cause, each with a test case and per-browser results. Search for
`[navigation-api-qa]` to find filed issues.

## Findings, ranked by impact

| # | Target | Finding |
|---|---|---|
| 01 | Gecko | [Content process crash reading `navigation.activation.entry` after traversing back into an opaque-origin document](findings/01-gecko-activation-entry-null-crash/finding.md). Reachable from a page via a sandboxed iframe; 108 reports on crash-stats (`NavigationActivation_Binding::get_entry`); Firefox 152 release affected. |
| 02 | Spec | [`navigation.activation` can have a null `entry` when entries and events are disabled](findings/02-spec-activation-entries-disabled/finding.md) (the spec gap behind 01; Chromium and WebKit return a null `activation`). |
| 03 | Spec (Safari TP follows it) | [An intercepted `navigation.navigate()` cancels an ongoing cross-document navigation](findings/03-spec-intercepted-navigate-cancels-cross-document/finding.md): with React DOM 19's default transition indicator active, a link click or `location.href` navigation with a response slower than ~20 ms does nothing in Safari TP; Chrome and Firefox navigate. |

<!-- page results summary filled below -->

## 1. Where the API is used (HTTP Archive, 2026-10-01 crawl)

- Blink's use counter `kNavigationAPI` (4056) fires on `navigate()`, `reload()`, `traverseTo()`,
  `back()`, `forward()`, `updateCurrentEntry()` and the `onnavigate` setter (`navigation.idl`
  `MeasureAs`, `NavigationApi::setOnnavigate`), not on `addEventListener("navigate")` or reads. It
  hit 44 desktop and 38 mobile root pages, 2 of all hits within rank 100k
  (`queries/01-counter-pages.sql`, `.csv`, 0.192 TiB processed). Too few to sample, and the crawl
  doesn't interact, so it misses listener-only use.
- Response bodies in `httparchive.sample_data.requests_10k` (the top 10k sites: 11,218 desktop and
  13,363 mobile pages) scanned for Navigation API tokens (`queries/02-sample10k-snippets.sql`,
  0.152 TiB; output gzipped). 19,294 of the 24,581 client-pages have at least one
  (`data/coverage.txt`, `data/tokens.txt`). `scripts/classify_libs.py` labels each page by the
  libraries behind the hits (`data/libs.txt`, `queries/02-sample10k-pages.csv`):
  - Google Tag Manager / gtag reading `navigation.entries()` (for click IDs): 16,386 client-pages.
  - Cloudflare Web Analytics beacon, `navigate` listener: 6,022. Google Publisher Tag,
    `navigatesuccess` listener: 5,197.
  - React DOM 19's default transition indicator (`navigate()` + `intercept()` while a transition
    is pending): 2,866. React's view-transition code reading `navigation.transition`: 1,560.
  - Smaller: geoedge (`navigate` listener that can `preventDefault()`), back-button interceptors
    (e.g. `s.trvdp.com`), Next.js app router (`navigation.activation.entry`), Steam's own router,
    Angular `PlatformNavigation`, Qwik City, Dynatrace, Amplitude, Contentsquare, Shopify pixels.
  - 69 desktop pages call `intercept()`, `navigate()`, `updateCurrentEntry()`, `traverseTo()`,
    `back()` or `precommitHandler` outside React's indicator (`data/active_pages.json`).

Numbers are recomputed from committed files by `scripts/recount.py`.

## 2. Live comparison

Setups (`navqa.py`): A and A2 Chrome Canary (headed, Playwright; A2 is the noise floor), B Firefox
Nightly (headless, Selenium + geckodriver, BiDi), C Firefox Nightly with
`dom.navigation.webidl.enabled=false` (separates Navigation API differences from other Gecko
differences), D Safari TP 255 (Selenium + safaridriver). 1280x800 viewport.

Each visit: load, dismiss common consent dialogs, then click a same-origin link (the one A
picked, when visible), a second link (batch 2), back (twice in batch 2), forward, reload, click a
fragment link or set `location.hash`, back. Per step: URL, whether the step stayed in the same
document, `history.length`, `navigation.entries()`/`currentEntry`/`transition`/`activation`,
scroll position, and a trace (`trace.js`, preloaded in A–C, injected after load in D) of
Navigation API calls, listeners, `navigate` events (type, `canIntercept`, `userInitiated`,
intercepted, cancelled) and their outcome, `popstate`/`hashchange`, and JS errors. Scrubbed at
capture; page text kept out of the repo.

Samples (seed 2026, `scripts/make_sample.py`): batch 1, 189 desktop pages stratified by library
(plus the 12 top-ranked Blink-counter pages); batch 2, 194 pages: the active-use pages not already
sampled and a second stratified draw. Analysis (`analyze_nav.py`) flags a metric for B or D when A
and A2 agree and the setup differs; a Firefox flag counts only when C agrees with A. Flagged pages
are rerun twice in A, B, C (`scripts/recheck_compare.py`).

Harness changes during the run (the data below is from the final versions): consent dismissal and
a wider link picker after a first try; Safari TP uses script clicks and `history.back()`, because
safaridriver's element click often didn't reach the page and its back skips entries created
without a user gesture; the state read skips `activation` in opaque-origin documents after it
triggered finding 01 (it crashed Firefox when a back landed on `about:blank`; those visits were
rerun).

### Page results

<!-- filled from recount.py -->

## 3. Local tests

`tests/` (served by `server.py`, run by `testrun.py` in each setup; results in `tests/results/`):

- React's default transition indicator (`react-transition-indicator.html`): history state, scroll,
  focus and entries are the same in all three engines (all three null `history.state` for the
  replaced entry).
- Cross-document click or `location.href` while the indicator runs: finding 03.
- `navigation.activation` and entry keys across `replaceState`, `pushState`, reload and returning
  from another page, as Next.js's app router assumes (`activation-keys.html`): same in all three.
- `navigation.activation` in opaque-origin documents: findings 01 and 02.
- Cancelling or intercepting a same-document back traversal, as back-button interceptors do
  (`traverse-cancel.html`): same in all three for script and WebDriver traversals. Firefox's
  toolbar back skips entries added without user interaction, so the browser-UI case wasn't
  testable this way.
- `intercept({scroll: "manual"})` on same-URL replace, push and other-URL navigations
  (`intercept-scroll-manual.html`): same in all three.

## Not covered

- Pages behind login, mobile, and interactions beyond link clicks, back/forward, reload and
  fragment changes (no form submissions on live sites). React's transition indicator never ran
  during the scripted visits.
- Browser-UI traversals: all setups traverse via WebDriver, CDP or script, which don't count as
  browser UI.
- Safari TP page comparisons are noisier than Firefox's: sites serve Safari different content
  and consent flows, and there is no API-off control for Safari.

## Reproduce

```sh
bq query --use_legacy_sql=false --format=csv --max_rows=100000 < queries/01-counter-pages.sql > queries/01-counter-pages.csv
bq query --use_legacy_sql=false --format=json --max_rows=1000000 < queries/02-sample10k-snippets.sql > queries/02-sample10k-snippets.json
python3 scripts/classify_libs.py queries/02-sample10k-snippets.json data/pages_libs.json
python3 scripts/make_sample.py 2026 samples/batch1.txt -- <stratum=n ...>
python3 -m venv .venv && .venv/bin/pip install selenium playwright warcio pillow
python3 server.py &
.venv/bin/python pipeline.py samples/batch1.txt out/b1 30      # A, then A2/B/C/D
.venv/bin/python analyze_nav.py out/b1 > analysis-b1.txt
.venv/bin/python testrun.py tests/<test>.html --setups A,B,C,D
.venv/bin/python scripts/recount.py
```

Live pages change, so a rerun won't match exactly. Screenshots and page text (`out/**/shots`,
`out/**/text`) aren't committed.
