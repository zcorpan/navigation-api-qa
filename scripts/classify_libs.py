"""Label each requests_10k page with the libraries that touch the Navigation API.

Usage: classify_libs.py queries/02-sample10k-snippets.json data/pages_libs.json
"""
import collections
import json
import re
import sys
from urllib.parse import urlsplit

# (label, url regex or None, snippet regex or None); first matching label per snippet wins.
SIGS = [
    ('youtube-custom-event', r'youtube(-nocookie)?\.com/s/', None),
    ('sw-false-positive', None, r'SENTRY_INTERCEPTED_URLS|respondWith'),
    ('gtm-entries', None, r'navigation&&\w+\.navigation\.entries&&'),
    ('cloudflare-beacon', r'static\.cloudflareinsights\.com', None),
    ('cloudflare-challenge', r'/cdn-cgi/challenge-platform/', None),
    ('react-transition-indicator', None, r'"react-transition"'),
    ('react-view-transition', None, r'startViewTransition.{0,200}navigation\.transition|navigation&&\w+\.navigation\.transition'),
    ('gpt', r'(doubleclick\.net|googlesyndication\.com)/pagead/managed', None),
    ('doubleverify', r'(doubleverify\.com|dv\.tech)/dvtag', None),
    ('ezoic', r'ezojs\.com', None),
    ('contentsquare', r'contentsquare\.net|clicktale\.net', None),
    ('ias-detect', r'adsafeprotected\.com', None),
    ('dynatrace', r'dynatrace|ruxitagent', r'globalThis\.navigation instanceof EventTarget'),
    ('amplitude', r'amplitude', r'addAdditionalEventProperties\(\w+,\s*[`"]navigate[`"]'),
    ('shopify-wpm', r'/wpm/', None),
    ('klaviyo', r'klaviyo\.com', None),
    ('tiktok', r'tiktokcdn|ttwstatic', r'"navigation_navigate"'),
    ('mgid', r'mgid\.com', None),
    ('seedtag', r'seedtag\.com', None),
    ('pushly', r'p-n\.io', None),
    ('stay22', r'stay22\.com', None),
    ('adscore-fp', r'adsco\.re', None),
    ('rokt', r'rokt-api\.com', None),
    ('steam', None, r'g_bUseNavigationAPI'),
    ('angular-platform-navigation', None, r'factory:\s*\(\)\s*=>\s*window\.navigation'),
    ('qwik-city', None, r'_qCity'),
    ('nextjs-activation', None, r'navigation\.activation\?\.entry'),
    ('back-intercept', None, r'"traverse"===\w+\.navigationType|navigationType\s*===\s*"traverse"'),
    ('activation-read', None, r'navigation\.activation'),
    ('nitrous', r'nitrous', None),
    ('geoedge', r'geoedge\.be', None),
    ('transcend-airgap', r'transcend-cdn\.com', None),
    ('perimeterx', r'px-cloud\.net|perimeterx', None),
    ('debugbear', r'debugbear\.com', None),
    ('membrana', r'membrana\.media', None),
    ('meta-rsrc', r'(fbcdn\.net|whatsapp\.net|cdninstagram\.com)/rsrc', None),
    ('iadvize', r'iadvize\.com', None),
    ('convert-fp', r'convertexperiments\.com', None),
]
SIGS = [(l, u and re.compile(u), s and re.compile(s)) for l, u, s in SIGS]


def labels_for(row):
    out = set()
    unmatched = False
    for snip in row['snippets']:
        for label, u, s in SIGS:
            if (u is None or u.search(row['url'])) and (s is None or s.search(snip)):
                out.add(label)
                break
        else:
            unmatched = True
    if unmatched and not out:
        out.add('other')
    return out


def main():
    rows = json.load(open(sys.argv[1]))
    pages = {}
    for r in rows:
        key = r['client'] + ' ' + r['page']
        p = pages.setdefault(key, {'client': r['client'], 'page': r['page'], 'rank': int(r['rank'] or 0),
                                   'is_root_page': r['is_root_page'], 'libs': {}})
        for label in labels_for(r):
            p['libs'].setdefault(label, []).append(r['url'])
    json.dump(sorted(pages.values(), key=lambda p: (p['rank'], p['page'], p['client'])), open(sys.argv[2], 'w'), indent=1)
    count = collections.Counter()
    top = collections.Counter()
    for p in pages.values():
        for label in p['libs']:
            count[label] += 1
            if p['rank'] <= 10000:
                top[label] += 1
    for label, n in count.most_common():
        print(f'{n:6} pages ({top[label]:4} rank<=10k)  {label}')


main()
