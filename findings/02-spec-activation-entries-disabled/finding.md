# [navigation-api-qa] `navigation.activation` can have a null `entry` when entries and events are disabled

Target: whatwg/html issue (spec).

## What's wrong

*update document for history step application*
(https://html.spec.whatwg.org/#update-document-for-history-step-application) step 7 creates or
updates `navigation`'s activation whenever *previousEntryForActivation* is given and
*navigationType* is non-null, without checking whether `navigation` has entries and events
disabled (https://html.spec.whatwg.org/#has-entries-and-events-disabled). Step 7.5 then sets the
activation's new entry to `navigation`'s current entry, which is null when entries and events are
disabled (opaque origin, initial `about:blank`). The `activation` getter
(https://html.spec.whatwg.org/#dom-navigation-activation) returns it, but
`NavigationActivation`'s `entry` attribute is non-nullable, so its getter has nothing valid to
return.

Reachable from web content: a sandboxed iframe (opaque origin) navigates to another document and
goes back; the recreated document reads `navigation.activation.entry`.

## Implementations

- Chromium returns null from the `activation` getter when entries and events are disabled
  (https://chromium.googlesource.com/chromium/src/+/6ca4e60b94475fa916dfb688608e6cc72693a1bf/third_party/blink/renderer/core/navigation_api/navigation_api.cc#110).
- Gecko follows the spec text and returns an activation whose `entry` is null, which crashes the
  content process ([finding 01](../01-gecko-activation-entry-null-crash/finding.md)).
- WebKit (Safari TP 255) returns a null `activation` in the same test.

## Test case

[`../01-gecko-activation-entry-null-crash/test.html`](../01-gecko-activation-entry-null-crash/test.html).

## Existing reports

None found in whatwg/html (searched "navigation.activation", "activation entries and events
disabled", "NavigationActivation entry null").
