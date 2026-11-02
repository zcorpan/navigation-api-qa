# An intercepted `navigation.navigate()` cancels an ongoing cross-document navigation, which breaks link clicks while React's transition indicator runs

Target: whatwg/html issue (spec). Safari TP follows the spec; Chrome Canary and Firefox Nightly
don't.

Filed: [whatwg/html#13173](https://github.com/whatwg/html/issues/13173). Related: [whatwg/html#12820](https://github.com/whatwg/html/issues/12820), [whatwg/html#11745](https://github.com/whatwg/html/issues/11745).

## What's wrong

In *navigate* (https://html.spec.whatwg.org/#navigate), step 20 sets the navigable's ongoing
navigation (which aborts other ongoing navigations) before step 22 fires the `navigate` event. So a
same-document `navigation.navigate()` that a handler intercepts still cancels a cross-document
navigation already in flight. WPT `navigation-api/navigate-event/intercept-stops-ongoing-cross-document-navigation.html`
expects that; on wpt.fyi it passes in Safari TP 255 and fails in Chrome 159 and Firefox 161
(`wpt/interop-failures.txt`).

React DOM's default transition indicator
(https://github.com/facebook/react/blob/76baa3b5434fad315ece9cfd4d20d7a8d6c34a25/packages/react-dom/src/client/ReactDOMDefaultTransitionIndicator.js#L42-L75)
runs while a transition is pending: it calls `navigation.navigate(currentEntry.url, {history:
"replace", info: "react-transition"})` and intercepts it with a promise that settles when the
transition ends. When that fake navigation ends with `navigateerror` (for example because the user
clicked a link, which aborts it), the indicator restarts it 20 ms later. If the user's navigation
is cross-document and its response takes longer than that, the restarted `navigate()` cancels it
under the spec's rule: the click, or a scripted `location.href` assignment, does nothing.

Two of the three engines don't implement the rule, and implementing it breaks this pattern.

## Test case

`test.html` (served by `server.py`, which provides `/slow?ms=N`): the React indicator code from
production bundles, then a click on a same-origin cross-document link whose response takes
`ms` milliseconds (`?slow=1&ms=150`), or a `location.href` assignment (`&how=location`).

| Browser | `?slow=1&ms=150` (native click) | `&js=1` (script click) | `&how=location` |
|---|---|---|---|
| Chrome Canary 159.0.8136.0 | leaves the page | leaves the page | leaves the page |
| Firefox Nightly 161.0a1 | leaves the page | leaves the page | leaves the page |
| Safari TP 255 | stays (navigation cancelled) | stays (navigation cancelled) | stays (navigation cancelled) |

Without the slow response (`page2.html`, served instantly) all three leave the page. Results:
`results/`.

## In the wild

The indicator code is in 2,866 of the HTTP Archive 10k sample's client-pages (React DOM 19
bundles, `react-transition-indicator` in `queries/02-sample10k-pages.csv`), including Pinterest,
Facebook/Instagram, Vinted and Next.js sites. It only runs while a React transition is pending; the
scripted page visits in this run never triggered it, so the crawl can't say how often users click a
cross-document link or a Next.js app does a hard navigation during one.

## Existing reports

None found in whatwg/html (searched "ongoing navigation intercept", "intercept cross-document
navigation ongoing"). Related: [whatwg/html#12820](https://github.com/whatwg/html/issues/12820) and [whatwg/html#11745](https://github.com/whatwg/html/issues/11745) (ongoing cross-document
navigations aren't observable, e.g. via `navigation.transition`; React's indicator skips its
restart only when `navigation.transition` is non-null). facebook/react couldn't be searched from
this account (GitHub search returned 422).
