# WebKit: `NavigateEvent.userInitiated` is false for cross-document link clicks (known: WebKit bug 306262)

Target: already filed as [WebKit bug 306262](https://webkit.org/b/306262) ("NavigationEvent#userInitiated
is only true for fragment links or form submissions"). Data point only.

## Cause

WebKit initializes `userInitiated` from `UserGestureIndicator::processingUserGesture()` when it
fires the event
(https://github.com/WebKit/WebKit/blob/15cb3560da6c863025957fce3ee065cf61902e75/Source/WebCore/page/Navigation.cpp#L1502),
not from the navigation's user involvement
(https://html.spec.whatwg.org/#inner-navigate-event-firing-algorithm step 21). For cross-document
navigations the event seems to fire after the click's gesture scope has ended. WPT
`navigation-api/navigate-event/navigate-anchor-{same-origin-cross-document,cross-origin,with-target}-userInitiated.html`
fail in Safari TP 255 only (`wpt/interop-failures.txt`).

## In the wild

323 client-pages in the HTTP Archive 10k sample read `userInitiated` (`data/feature-usage.txt`),
mostly geoedge's ad-quality script (278), which reports
non-user-initiated cross-host navigations as suspicious redirects, and PerimeterX (34), which
collects it as a signal. Nothing user-visible was seen in this run (Safari TP visits used script
clicks, so their `userInitiated` couldn't be compared).
