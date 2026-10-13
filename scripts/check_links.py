#!/usr/bin/env python3
"""Check that every external link in the guides, topics, and source directory still opens.

This is a maintenance aid, not a content check. A page that loads can still have moved its
documents. Some sites block automated requests; those are reported as "blocked", not broken.
Run it from a normal network connection. FDA returns 404 to cloud CI runners, so a scheduled
GitHub Actions check reports false failures.

Usage: python scripts/check_links.py [--json report.json]
"""
import argparse
import concurrent.futures
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')


def collect():
    links = {}

    def add(url, where):
        if url.startswith('http'):
            links.setdefault(url, set()).add(where)

    for path in sorted((root / 'content/guides').glob('*.yaml')):
        g = yaml.safe_load(path.read_text(encoding='utf-8'))
        for item in (g.get('where') or []) + (g.get('also') or []):
            add(item['url'], f'guide:{g["id"]}')
    for path in sorted((root / 'content/topics').glob('*.yaml')):
        t = yaml.safe_load(path.read_text(encoding='utf-8'))
        for src in t.get('sources') or []:
            add(src['url'], f'topic:{t["id"]}')
    sources = json.loads((root / 'skills/mr-safety-agent/references/sources.json').read_text(encoding='utf-8'))
    for s in sources['sources']:
        add(s['url'], f'source:{s["id"]}')
    return links


def check(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            final = resp.geturl()
            return {'status': resp.status, 'final': final if final != url else None}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'final': None}
    except Exception as e:  # network errors, TLS, timeouts
        return {'status': None, 'error': type(e).__name__}


def classify(r):
    s = r.get('status')
    if s is None:
        return 'error'
    if s in (401, 403, 429):
        return 'blocked'
    if s >= 400:
        return 'broken'
    return 'redirected' if r.get('final') else 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', help='write a full report to this file')
    args = ap.parse_args()
    links = collect()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(links, pool.map(check, links)))
    rows = []
    for url, r in sorted(results.items()):
        rows.append({'url': url, 'result': classify(r), **r, 'used_by': sorted(links[url])})
    counts = {}
    for row in rows:
        counts[row['result']] = counts.get(row['result'], 0) + 1
    print(f'Checked {len(rows)} links: ' + ', '.join(f'{k} {v}' for k, v in sorted(counts.items())))
    for row in rows:
        if row['result'] in ('broken', 'error', 'redirected', 'blocked'):
            detail = row.get('final') or row.get('error') or row.get('status')
            print(f'- {row["result"]}: {row["url"]} -> {detail} ({", ".join(row["used_by"])})')
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    return 1 if counts.get('broken') or counts.get('error') else 0


if __name__ == '__main__':
    sys.exit(main())
