-- Pages hitting Blink use counter kNavigationAPI (4056) in the 2026-10-01 crawl, both clients, root and secondary pages.
SELECT client, is_root_page, page, rank
FROM `httparchive.crawl.pages`
WHERE date = '2026-10-01'
  AND EXISTS(SELECT 1 FROM UNNEST(features) WHERE id = '4056' AND type = 'default')
ORDER BY client, rank, page
