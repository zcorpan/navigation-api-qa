-- Navigation API usage in httparchive.sample_data.requests_10k (2026-10-01, ~11k desktop + ~13k mobile pages):
-- one row per response body with a distinctive Navigation API token, with up to 20 snippets of context.
WITH hits AS (
  SELECT client, page, is_root_page, rank, url, type,
    FARM_FINGERPRINT(response_body) AS body_fp,
    LENGTH(response_body) AS body_len,
    REGEXP_EXTRACT_ALL(response_body,
      r'.{0,160}(?:currententrychange|navigatesuccess|navigateerror|canIntercept|\bNavigateEvent\b|NavigationHistoryEntry|navigation\.currentEntry|navigation\.entries\(\)|navigation\.transition|navigation\.updateCurrentEntry|navigation\.traverseTo|["\x27]navigation["\x27]\s*in\s*(?:window|self|globalThis)|window\.navigation\b|globalThis\.navigation\b|self\.navigation\b|addEventListener\(\s*["\x27]navigate["\x27]|\.intercept\(\s*\{).{0,160}') AS snippets
  FROM `httparchive.sample_data.requests_10k`
  WHERE response_body IS NOT NULL
    AND REGEXP_CONTAINS(response_body, r'currententrychange|navigatesuccess|navigateerror|canIntercept|\bNavigateEvent\b|NavigationHistoryEntry|navigation\.currentEntry|navigation\.entries\(\)|navigation\.transition|navigation\.updateCurrentEntry|navigation\.traverseTo|["\x27]navigation["\x27]\s*in\s*(?:window|self|globalThis)|window\.navigation\b|globalThis\.navigation\b|self\.navigation\b|addEventListener\(\s*["\x27]navigate["\x27]|\.intercept\(\s*\{')
)
SELECT client, page, is_root_page, rank, url, type, body_fp, body_len,
  ARRAY_LENGTH(snippets) AS n_snippets,
  ARRAY(SELECT s FROM UNNEST(snippets) s WITH OFFSET o WHERE o < 20) AS snippets
FROM hits
