# [navigation-api-qa] WebDriver Refresh in Firefox does a cache-bypassing reload, so the scroll position isn't restored

Target: Bugzilla, Remote Protocol :: Marionette. Automation only.

## What's wrong

WebDriver Refresh (https://w3c.github.io/webdriver/#refresh) initiates "an overridden reload" of
the active document. Marionette's `navigate.refresh` reloads with
`Ci.nsIWebNavigation.LOAD_FLAGS_BYPASS_CACHE`
(https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/remote/marionette/navigate.sys.mjs#185),
the flag for a forced (Shift+Reload) reload, so it bypasses the cache and Firefox doesn't restore
the scroll position. A script `location.reload()` in the same Firefox restores it, as do Chrome's CDP
reload and Safari TP's WebDriver Refresh.

## Test case

`../../tests/reload-scroll.html` (via `testrun.py`): scroll to 3000px, reload, report `scrollY`
after load.

| | `?how=script` (`location.reload()`) | `?how=driver` (WebDriver Refresh / CDP reload) |
|---|---|---|
| Chrome Canary 159.0.8136.0 | 3000 | 3000 |
| Firefox Nightly 161.0a1 | 3000 | 0 |
| Firefox Nightly, Navigation API off | 3000 | 0 |
| Safari TP 255 | 3000 (0 at `load`, restored after) | 3000 (0 at `load`, restored after) |

## In the wild

In this run it showed up as Firefox (with and without the Navigation API) at a different `scrollY`
than Chrome after the reload step on 38 pages, mostly 0 where Chrome restored the position
(`data/engine_diffs.json`, metric `scrollY`, step `reload`), and in the fragment and back steps
after it.

## Existing reports

None found (Bugzilla quicksearch for "marionette refresh bypass cache", "WebDriver refresh
LOAD_FLAGS_BYPASS_CACHE", "refresh scroll position marionette").
