# Content process crash reading `navigation.activation.entry` after traversing back into an opaque-origin document

Target: Bugzilla, Core :: DOM: Navigation (crash; `nsWrapperCache::GetWrapperMaybeDead` in `NavigationActivation_Binding::get_entry`).

Filed: [bug 2088099](https://bugzil.la/2088099). Spec issue: [whatwg/html#13172](https://github.com/whatwg/html/issues/13172).

## What's wrong

In a document whose `Navigation` has entries and events disabled (opaque origin, e.g. a `data:`
document in a sandboxed iframe, or `about:blank`), Firefox exposes a non-null
`navigation.activation` after the document is reached by a traversal, and its non-nullable `entry`
is null. Reading `navigation.activation.entry` dereferences null in the binding (SEGV at 0x10) and
the content process crashes.

`Navigation::GetActivation()` returns `mActivation` unconditionally
(https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/dom/navigation/Navigation.cpp#319),
and the activation's new entry is set from `GetCurrentEntry()`, which is null when entries and
events are disabled
(https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/dom/navigation/Navigation.cpp#2353),
while `entry` is non-nullable in the IDL
(https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/dom/webidl/NavigationActivation.webidl#12).

Chromium returns null from the `activation` getter in that state
(`return HasEntriesAndEventsDisabled() ? nullptr : activation_;`,
https://chromium.googlesource.com/chromium/src/+/6ca4e60b94475fa916dfb688608e6cc72693a1bf/third_party/blink/renderer/core/navigation_api/navigation_api.cc#110).
The spec's *update document for history step application* step 7 doesn't check for entries and
events disabled either, so the spec can produce the same null `entry` (see
[finding 02](../02-spec-activation-entries-disabled/finding.md)).

## Test case

`test.html` (serve over HTTP, e.g. `python3 server.py`; results in `results/`): a sandboxed iframe (`allow-scripts`) loads a `data:` document,
navigates to a second `data:` document, which calls `history.back()`; the recreated first document
reads `navigation.activation` and `navigation.activation.entry` and posts the result to the parent.

| Browser | Result |
|---|---|
| Chrome Canary 159.0.8136.0 | `{"activation": "null", "type": null, "entry": "no activation"}` |
| Firefox Nightly 161.0a1 | content process crash |
| Firefox 152.0.3 | content process crash |
| Firefox Nightly, `dom.navigation.webidl.enabled=false` | no `navigation` (not affected) |
| Safari TP 255 | `{"activation": "null", "type": null, "entry": "no activation"}` |

`webdriver-repro.py` reproduces it at top level: WebDriver navigates to `about:blank` (or a
`data:` URL), then to any page, goes back, and reads `navigation.activation.entry`.

## In the wild

- Crash reports: 108 crashes with `NavigationActivation` in the proto signature
  (crash-stats Super Search, proto signature contains `NavigationActivation`), signature
  `nsWrapperCache::GetWrapperMaybeDead`, frame 1 `NavigationActivation_Binding::get_entry`
  (e.g. https://crash-stats.mozilla.org/report/index/9dd27c8b-75e0-4ad7-b1d6-31b080261101,
  Fenix 159.0). Mostly release (96), mostly Android (81).
- Scripts that read `navigation.activation`: 237 client-pages in the HTTP Archive 10k sample
  (`data/feature-usage.txt`), including Next.js's app router, which reads `activation.entry` in
  `hasMissedTraversal()` (`packages/next/src/client/components/app-router.tsx`; 133 client-pages,
  `nextjs-activation` in `queries/02-sample10k-pages.csv`). Any of them in an opaque-origin
  document (sandboxed iframe without `allow-same-origin`, or a page served with CSP `sandbox`) that
  is reached by a traversal would crash the tab.
- In this run the harness itself hit it whenever a back landed on `about:blank` and it read
  `activation.entry`: rerunning 17 affected pages one per fresh session, Firefox (API on) died on
  14; with the read skipped in opaque-origin documents, on 0 (3 network errors); Firefox (API off)
  on 0 (3 network errors) (`data/crash/`).

## Existing reports

No Bugzilla bug found for this signature with `NavigationActivation` (searched
`cf_crash_signature` for `GetWrapperMaybeDead`: [bug 2063234](https://bugzil.la/2063234) is a different stack,
`ShadowRoot_Binding::get_host`). No whatwg/html issue found.
