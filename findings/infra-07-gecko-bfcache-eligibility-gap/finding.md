# Firefox restores fewer top-10k pages from bfcache on back than Chrome and Safari TP (data for known bugs)

Target: data point for existing Bugzilla bugs (Core :: DOM: Navigation): [bug 1896663](https://bugzil.la/1896663) (in-flight
requests), [bug 1712380](https://bugzil.la/1712380) and [bug 1741670](https://bugzil.la/1741670) (unload listeners on desktop), [bug 2072126](https://bugzil.la/2072126) (MSE content). No new bug.

## Measurement

80 batch-1 pages (seeded, `samples/bfcache-80.txt`) whose first same-origin link navigated in
Chrome: load, click the link, back, forward. Chrome Canary with bfcache enabled (setup A3;
Playwright disables it by default), Firefox Nightly with and without the Navigation API using W3C
pointer-action clicks (Element Click leaves an unload listener, see
[infra-04](../infra-04-marionette-click-unload-listener/finding.md)), Safari TP 255 (script
clicks, `history.back()`). Restored from bfcache = a `pageshow` with `persisted` true
(`data/bfcache/back-patterns.json`, records in `out/bf/`, Safari TP's in `out/b1/D`).

| | back restored from bfcache | forward restored from bfcache |
|---|---|---|
| Chrome Canary 159.0.8136.0 (bfcache on) | 32 / 79 | 26 / 79 |
| Firefox Nightly 161.0a1 | 18 / 77 | 19 / 77 |
| Firefox Nightly, Navigation API off | 16 / 77 | 22 / 77 |
| Safari TP 255 | 38 / 74 | 41 / 74 |

On 10 pages Chrome and Safari TP restored the page on back and Firefox (API on and off) didn't.
Firefox's logged reasons (`MOZ_LOG=SHIPBFCache:5`, `data/bfcache/scan-gap.jsonl`) on the 8 of
them with a logged decision: requests in flight when leaving (5: flashscore.sk, mos.jp,
franceinfo.fr, phe69.shop, cloud.mail.ru), unload listener (4: lavuelta.es, faberlic.com,
cloud.mail.ru, phe69.shop), MSE use (2: Steam app page, faberlic.com).

The Navigation API made no systematic difference (API on vs off differ both ways, 4 vs 2 pages).
One case where it did: on razorpay.com/engage, with the API on, a Segment track request
(`api.segment.io/v1/t`) sent at navigation time was still in flight when the page was left, so it
wasn't cached; with the API off, no request was in flight and it was (logs from
`scripts/bfcache_log.py`, not committed).

## Existing reports

[Bug 1896663](https://bugzil.la/1896663) (ASSIGNED, patches in review) covers in-flight requests; [bugs 1712380](https://bugzil.la/1712380) and [1741670](https://bugzil.la/1741670)
cover unload listeners on desktop (`docshell.shistory.bfcache.allow_unload_listeners` is true only
on Android); [bug 2072126](https://bugzil.la/2072126) covers MSE.
