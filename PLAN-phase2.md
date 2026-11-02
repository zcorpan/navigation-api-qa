# QA run, phase 2: Navigation API beyond the top 10k, on mobile, with new interactions

## Context

Phase 1 is done and pushed to `zcorpan/navigation-api-qa` (local `~/git/zcorpan/navigation-api-qa`). It drove 382 top-10k desktop pages in Chrome Canary, Firefox Nightly (API on/off) and Safari TP 255. It found 3 Navigation API findings (01 Gecko crash, 02 spec, 03 spec/Safari TP), plus infra-04 to infra-07. Its limits were desktop only and top 10k only. Its interactions also barely reached the active API: link clicks, WebDriver/CDP back, reload and fragment, with `intercept()` on 2–4 pages and React's indicator never.

Phase 2 extends the same run with three things: pages beyond the top 10k, both desktop and emulated mobile, and new interactions, especially browser-UI back/forward/reload, form submission, keyboard, touch and modifier clicks.

The same rules apply: report problems only, with no fix suggestions. Prefer breadth once a cause is known. Write one fileable `findings/<id>/` per bug: Navigation API findings continue at 04, infrastructure findings at infra-08. Nothing is filed or pushed unless asked.

## Step 0: before the user leaves

- **iOS Simulator, for mobile WebKit (user chose this).** `simctl` fails because CoreSimulator isn't installed. The user runs `! sudo xcodebuild -runFirstLaunch` and `! xcodebuild -downloadPlatform iOS`. I then boot an iPhone simulator. The user turns on Settings > Safari > Advanced > Remote Automation in it, and I check `safaridriver` with `platformName: iOS`, `safari:useSimulator: true`.
- **Smoke test every new backend on local pages, and report.** If one fails, change the plan before starting:
  - **Chrome desktop UI traversals:** an unpacked extension (`ext/`, MV3 service worker) in Canary via `launch_persistent_context` with `--load-extension`. Branded Canary also needs `--disable-features=DisableLoadExtensionCommandLineSwitch`. `chrome.tabs.goBack/goForward/reload` is called through `ctx.service_workers[0].evaluate`. Check that it skips entries added without user activation like the toolbar does, while Playwright's `go_back` doesn't. Fallback: run the Chrome setups on Playwright's bundled Chromium (`chromium-1243`) and say so.
  - **Firefox UI traversals:** chrome context `gBrowser.goBack()/goForward()` and `BrowserCommands.reload()`. `Firefox.uiback` in `navqa.py` already does back, using `--allow-system-access`.
  - **Safari TP UI traversals and clicks:** do W3C pointer-action clicks reach the page on about 10 real sites, unlike element click? If they do, `driver.back()` serves as the UI traversal, since it skips gesture-less entries. If not, Safari TP's UI steps are only compared in local tests.
  - **Mobile emulation probe page:** check UA, `innerWidth` under `<meta name=viewport>`, `matchMedia('(pointer: coarse)')`, `ontouchstart`, DPR and a touch tap, compared across the setups.

Query budgets were pre-approved: dry-run every query and pass `--maximum_bytes_billed`, without stopping to ask.

## Setups

These are new defaults for phase 2, so earlier artifacts don't recur. Chrome runs with bfcache on: drop Playwright's `--disable-back-forward-cache`, as A3 did. Firefox clicks with pointer actions (`NAVQA_FF_CLICK=actions`, avoiding infra-04).

| | Desktop 1280x800 | Mobile, emulated |
|---|---|---|
| Chrome Canary | A, A2 | Am, A2m: Playwright `is_mobile`, `has_touch`, 360x640 viewport, DPR 3, Android Chrome UA with Canary's version (as HTTP Archive's mobile crawl) |
| Firefox Nightly | B; C API off | Bm; Cm API off. 360x640 inner window and Firefox Android UA (`general.useragent.override`). Prefs: `dom.meta-viewport.enabled`, `dom.w3c_touch_events.enabled=1`, coarse-pointer `ui.*PointerCapabilities`, `layout.css.devPixelsPerPx=3`, `docshell.shistory.bfcache.allow_unload_listeners=true` (Android default). It's still desktop Gecko, not Fenix; the README says so. |
| WebKit | D Safari TP 255 | Dm Safari on the iOS Simulator (release Safari, version recorded) |

Mobile setups tap with touch input: Playwright `tap`, Firefox and safaridriver pointer actions of type touch. Add `MobileChrome` and `MobileFirefox` subclasses and an `IOSSafari` backend to `navqa.py` (`BACKENDS`). `pipeline.py` gets mobile follower sets.

Parallelism: Chrome and Firefox get up to 4 lanes each (14 cores, 48 GB). D and Dm run one session each, in parallel with each other.

## New interactions (`navqa.py` `STEPS`, `NAVQA_STEPS=v3`)

| Step | What happens |
|---|---|
| load | as before |
| link | scroll to 1200px, then a real click or tap on a same-origin link |
| link2 | as before |
| keyboard | focus a same-origin link and press Enter |
| uiback, uiback2, uiforward | browser-UI traversals (backend `uiback/uiforward`) |
| search | GET search form only: same-origin action, one text/search input named like q/s/query/search, no password field. Types "news" with real key events, then Enter. Search the PICK_JS way, with a new `FORM_JS` |
| uiback-search | UI back |
| modclick | Cmd-click (Ctrl elsewhere) on a same-origin link. Record whether this tab navigated and the tab count, then close extra tabs |
| uireload | browser-UI reload |
| fragment, back2 | as before; `back2` uses `history.back()` |

New per-step fields: `leftSite` (top-level origin changed), `tabs`, the step's input method. `trace.js` already records each navigate event's `formData`, `sourceElement`, `userInitiated`, `cancelable` and `defaultPrevented`. `analyze_nav.py` gets these as metrics. For back interceptors the key one is whether two UI backs after a real click leave the site.

## Sources beyond the top 10k

1. **`queries/03-longtail-pages.sql` (1.5 GB, dry-run).** A seeded list (`FARM_FINGERPRINT(CONCAT(page,'2026'))`) of 2026-10-01 root pages with rank > 10k, per client and rank bucket.
2. **`queries/04-counter-pages-aug-sep.sql` (0.38 TiB).** Counter 4056 hits on the 2026-08-01 and 2026-09-01 crawls, both clients, root and secondary pages. Combined with `queries/01` (2026-10-01, 152 pages), these are active callers at every rank.
3. **`queries/05-lib-script-urls.sql` (0.16 TiB).** Reads `requests.url` only. It finds pages loading script hosts whose Navigation API code changes navigations: geoedge, back-button interceptor hosts and others with a URL signature in `scripts/classify_libs.py`/`data/pages_libs.json`.
4. **Local Common Crawl.** `~/git/commoncrawl/cc-data/CC-MAIN-2026-39`, 12 WARCs, about 250k pages including deep pages. Inline scripts with active tokens (navigate listener with `intercept`/`preventDefault`, `navigation.navigate`/`traverseTo`/`back`) give inline back interceptors and routers. The new `scripts/cc_scan.py` is a regex prefilter, then a parse.
5. **Live detection pass (`scripts/detect.py`).** Chrome headless with the matching client emulation visits about 500 pages per rank stratum per client from source 1 (10k–100k, 100k–1M, 1M–10M, >10M), load only. It applies query 02's regex to every script/HTML response body and labels pages with `classify_libs.labels_for`, plus trace.js calls and listeners, written to `data/detect-<client>.jsonl`. This replicates the top-10k body scan for any page and gives long-tail usage rates per stratum.

## Batches (`scripts/make_sample.py`, seed 2026), ordered by rank weight

1. **Batch 3: the top-10k active pages on v3.** The 69 desktop pages from `data/active_pages.json`, plus their mobile-client counterparts from `queries/02` output, in desktop and mobile setups.
2. **Batch 4: a mobile top-10k stratified sample**, about 150 pages from the 13,363 mobile client-pages, by library as in batch 1.
3. **Batches 5 and 6: long tail, desktop and mobile, about 200 each.** All active pages from sources 2–5 first, then React indicator, back interceptor, Next.js and router strata, then about 20 passive pages.
4. More long-tail batches while new causes appear.

Stop after two consecutive batches with no new cause, with at least one long-tail batch per client done.

Flagged pages get two reruns in the reference, candidate and control setups (`scripts/recheck_compare.py`). Firefox flags count only when the API-off control agrees with Chrome. WebKit flags count when the API-level trace differs.

## Local tests (`tests/`, `testrun.py`, all desktop and mobile setups)

One page per new interaction, covering cases pages may lack:
- `form-navigate.html`: GET and POST forms, checking `formData` and `canIntercept`, intercepted POST, then back.
- `ui-traverse-cancel.html`: UI back with and without history-action activation, checking `cancelable`, the effect of `preventDefault()` and skipping of gesture-less entries. This is the case phase 1 couldn't test.
- `ui-reload.html`: the navigate event's type, `userInitiated` and `cancelable`, and intercepting a reload.
- `modifier-click.html`: Cmd, Ctrl, Shift and middle click while the page intercepts navigations. The source page must not navigate.
- `keyboard-link.html` (Enter: `userInitiated`, `sourceElement`), `download-link.html` (`downloadRequest`, `canIntercept`), `touch-tap.html`.
- `back-during-intercept.html`: UI back while an intercept handler is pending.

Results go to `tests/results/`. For each cross-browser disagreement, read the spec steps with `webspec-index` and check wpt.fyi to decide which engine deviates or whether it's a spec finding.

## Deliverables

- Commit the queries and outputs (bytes processed, no billing info), `data/detect-*.jsonl`, CC scan output, samples, `out/b3…`, the tests and the new findings.
- README: new sections for long-tail usage rates per stratum, mobile, the new interactions and per-setup counts. Every number gets recomputed by an extended `scripts/recount.py`.
- Phase 1 findings stay. A phase 2 page that only re-hits a known cause gets tagged and skipped.
- In chat: ranked findings, Navigation API and infra listed separately.

## Verification

- Smoke tests from step 0 pass, plus a sanity run of `tests/plain-link.html` in every setup before each batch.
- A vs A2 (and Am vs A2m) as the noise floor. Two reruns of every flagged page.
- Each finding's reduced test reproduces as stated in each browser, with engine code cited at a commit.
- `publish_check.py` passes before any commit (hook) and on full history before any push. Pushing to the public repo only when the user asks.
