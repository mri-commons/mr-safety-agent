#!/usr/bin/env python3
"""Check whether the documents each guide points to are still the current editions.

Each guide can list `watch` entries recording the edition it was written against. This script
looks at the manufacturer's site the same way a reader would and reports whether that edition is
still what is served. A change does not mean the guide is wrong. It means a person should reopen
the document and update the guide.

Entry types:
  pdf       Download the PDF and confirm its text still contains `expect` (catches in-place updates).
  page      Fetch a listing page and confirm it still contains `expect` (a file name or number).
  redirect  Follow a "latest version" link and confirm the final URL contains `expect`.
  medtronic Search Medtronic's US MRI Resource Library (`by`: model or brand) and confirm the
            results still link `expect`.

Run from a normal network connection; some sites block cloud CI runners.
Usage: python scripts/check_editions.py [--guide ID]
"""
import argparse
import http.cookiejar
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')


def squash(text):
    """Compare text without whitespace or case; PDF extraction often drops or adds spaces."""
    return re.sub(r'\s+', '', text).lower()


def opener():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [('User-Agent', UA), ('Accept', '*/*'), ('Accept-Language', 'en-US,en;q=0.9')]
    return op


def fetch(url, op=None, data=None):
    op = op or opener()
    with op.open(url, data=data, timeout=60) as resp:
        return resp.geturl(), resp.read()


def pdf_text(data):
    start = data.find(b'%PDF')
    if start < 0:
        raise ValueError('response is not a PDF')
    data = data[start:]  # some servers wrap the file in a multipart body
    gs = shutil.which('gs')
    if gs:
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / 'doc.pdf', Path(tmp) / 'doc.txt'
            src.write_bytes(data)
            subprocess.run([gs, '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=txtwrite',
                            f'-sOutputFile={out}', str(src)], check=True, capture_output=True)
            return out.read_text(encoding='utf-8', errors='ignore')
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('install Ghostscript or pypdf to read PDFs') from exc
    import io
    return '\n'.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(data)).pages)


def medtronic_search(by, query):
    base = 'https://manuals.medtronic.com/manuals/mri/en_US'
    op = opener()
    _, home = fetch(base + '/home/index', op)
    home = home.decode('utf-8', 'ignore')
    token = re.search(r'name="SYNCHRONIZER_TOKEN"[^>]*value="([^"]+)"', home)
    if not token:
        raise RuntimeError('library form token not found')
    form = {'findby': by, 'SYNCHRONIZER_TOKEN': token.group(1),
            'SYNCHRONIZER_URI': '/manuals/mri/en_US/home/index',
            ('querymodel' if by == 'model' else 'querybrand'): query}
    _, html = fetch(base + '/search/index', op, urllib.parse.urlencode(form).encode())
    html = html.decode('utf-8', 'ignore')
    if 'Manual Language for' in html:
        _, html = fetch(base + '/search/selectLang?manualLang=en', op)
        html = html.decode('utf-8', 'ignore')
    return html


def check(entry):
    kind, expect = entry['type'], entry['expect']
    if kind == 'pdf':
        _, data = fetch(entry['url'])
        found = squash(expect) in squash(pdf_text(data))
    elif kind == 'page':
        _, data = fetch(entry['url'])
        found = squash(expect) in squash(data.decode('utf-8', 'ignore'))
    elif kind == 'redirect':
        final, _ = fetch(entry['url'])
        found = expect.lower() in urllib.parse.unquote(final).lower()
    elif kind == 'medtronic':
        found = expect.lower() in medtronic_search(entry.get('by', 'model'), entry['query']).lower()
    else:
        raise ValueError(f'unknown watch type {kind}')
    return 'unchanged' if found else 'changed'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guide', help='check one guide id')
    args = ap.parse_args()
    results, unwatched = [], []
    for path in sorted((root / 'content/guides').glob('*.yaml')):
        guide = yaml.safe_load(path.read_text(encoding='utf-8'))
        if args.guide and guide['id'] != args.guide:
            continue
        watch = guide.get('watch') or []
        if not watch:
            unwatched.append(guide['id'])
        for entry in watch:
            try:
                status = check(entry)
            except (urllib.error.URLError, OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                status = f'unreachable ({type(exc).__name__}: {str(exc)[:80]})'
            results.append((guide['id'], entry['document'], entry['expect'], status))
    for gid, doc, expect, status in results:
        mark = {'unchanged': 'ok     '}.get(status, 'CHECK  ')
        print(f'{mark} {gid}: {doc} [{expect}] {status}')
    if unwatched:
        print('Needs a manual check (no automated watch): ' + ', '.join(unwatched))
    changed = [r for r in results if r[3] != 'unchanged']
    print(f'{len(results)} editions checked, {len(changed)} need review.')
    return 1 if changed else 0


if __name__ == '__main__':
    sys.exit(main())
