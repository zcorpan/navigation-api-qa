# WebDriver Element Click leaves an `unload` listener on the page, which makes it ineligible for bfcache

Target: Bugzilla, Remote Protocol :: Marionette. Automation only (not web-facing), but it changes
what bfcache, back/forward and Navigation API (`navigation.activation`, `pageshow.persisted`)
tests observe in Firefox.

Filed: [bug 2088100](https://bugzil.la/2088100).

## What's wrong

`interaction.flushEventLoop` adds an `unload` listener with `{ mozSystemGroup: true }`
(https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/remote/marionette/interaction.sys.mjs#462)
and removes it without that option
(https://searchfox.org/firefox-main/rev/e924f94175311819d7b549a732d0d8ee1263b31d/remote/marionette/interaction.sys.mjs#467),
so the removal doesn't match and the listener stays (the `click` listener the same way). After any
Element Click on a page, Firefox treats the page as having an unload listener for the rest of its
lifetime, and navigating away doesn't put it in bfcache, whether or not the click navigated.

## Test case

`repro.py` (with `python3 server.py` serving the repo): load `test.html`, optionally click a button
that does nothing, navigate away from a page timer, go back, and read Firefox's bfcache decision
for `test.html` from `MOZ_LOG=SHIPBFCache:5`. Result (`results.txt`), Firefox Nightly 161.0a1:

| Before navigating away | bfcache decision |
|---|---|
| no click | not blocked |
| WebDriver Element Click on the button | blocked: unload listener |
| W3C pointer actions click on the button | not blocked |

## In the wild

In this run every Firefox link step first used Element Click. Leaving a page that way, Firefox's
logged decision was "blocked" on 24 of 24 logged departures, 23 citing the unload listener
(`data/bfcache/scan-b1.jsonl`), and Firefox restored 3 of 257 pages from bfcache on back
(batches 1 and 2, `out/b*/B`). With pointer-action clicks on 80 of those pages it restored 18 of
77 ([infra-07](../infra-07-gecko-bfcache-eligibility-gap/finding.md)).

## Existing reports

None found (Bugzilla quicksearch for "marionette click unload listener bfcache",
"interaction.flushEventLoop", "element click bfcache").
