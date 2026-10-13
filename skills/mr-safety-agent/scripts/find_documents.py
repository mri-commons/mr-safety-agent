#!/usr/bin/env python3
"""Find and read manufacturer MRI documents that ordinary web fetching cannot reach.

Python standard library only. PDF reading uses Ghostscript (gs) if it is installed.

  medtronic --model W1DR01             Search Medtronic's US MRI Resource Library by model
  medtronic --brand Strata             ...or by product name (also --library main for the full library)
  bsci EMBLEM                          Search Boston Scientific's US product literature library
  biotronik "ProMRI System" [--all]    List BIOTRONIK US manual revisions for a product (* = current)
  integra "CERTAS Plus" [--fast]       Search Integra's eIFU portal (US); shows most recent or superseded
  abbott "MRI Procedure Information Proclaim" [--all] [--loose]
                                       Search Abbott's eIFU library (US); --all adds superseded editions
  inspire [--query MRI]                List Inspire's current English - US manuals with revisions
  redirect URL                         Show where a "latest version" link currently points
  pdf URL [--find TEXT] [--text N|N-M] [--render N]
                                       Download a PDF (cached), print its first and last page text
                                       (where identity lines usually are), find phrases with
                                       page numbers, print whole pages, and render pages to PNG
                                       for tables (repeat --find, --text, and --render for several)

Results are leads, not verification: open the document and read its identity before use.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')


def opener():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    op.addheaders = [('User-Agent', UA), ('Accept', '*/*'), ('Accept-Language', 'en-US,en;q=0.9')]
    return op


def get(op, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with op.open(req, timeout=60) as resp:
        return resp.geturl(), resp.read()


def text(b):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', b))).strip()


def medtronic(args):
    lib = 'mri' if args.library == 'mri' else 'main'
    base = f'https://manuals.medtronic.com/manuals/{lib}/{args.region}'
    op = opener()
    _, home = get(op, base + '/home/index')
    home = home.decode('utf-8', 'ignore')
    token = re.search(r'name="SYNCHRONIZER_TOKEN"[^>]*value="([^"]+)"', home)
    if not token:
        sys.exit('Library form not found; the site may have changed.')
    by, query = ('model', args.model) if args.model else ('brand', args.brand)
    form = {'findby': by, 'SYNCHRONIZER_TOKEN': token.group(1),
            'SYNCHRONIZER_URI': f'/manuals/{lib}/{args.region}/home/index',
            ('querymodel' if by == 'model' else 'querybrand'): query}
    _, page = get(op, base + '/search/index', urllib.parse.urlencode(form).encode())
    page = page.decode('utf-8', 'ignore')
    if 'Manual Language for' in page:
        _, page = get(op, base + '/search/selectLang?manualLang=en')
        page = page.decode('utf-8', 'ignore')
    page = re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S)
    found = []
    for href, label in re.findall(r'href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', page, flags=re.S):
        found.append((text(label), href))
    for href in re.findall(r"openDialogOptIn\([^)]*?'(https?://[^']+\.pdf[^']*)'", page):
        found.append(('(document)', href))
    found = list(dict.fromkeys(found))
    print(f'Medtronic {lib} library {args.region}, {by} "{query}": {len(found)} PDF links')
    for label, href in found:
        print(f'- {label[:110]}\n  {href}')
    if not found:
        print('No PDF links. Try --brand with the product name, or --library main.')


def bsci(args):
    op = opener()
    page_url = f'https://www.bostonscientific.com/elabeling/{args.country}/en/home/healthcare-professionals.html'
    _, page = get(op, page_url)
    token = re.search(r'searchTokenStripped\s*=\s*"([^"]+)"', page.decode('utf-8', 'ignore'))
    if not token:
        sys.exit('Search token not found on the library page; the site may have changed.')
    body = urllib.parse.urlencode({
        'q': args.query, 'searchHub': 'elabeling_HCP', 'locale': 'en', 'numberOfResults': args.count,
        'firstResult': 0, 'sortCriteria': 'relevancy',
        'context': json.dumps({'country': args.country, 'locale': 'en', 'audience': 'healthcare-professionals',
                               'aem_environment': 'www.bostonscientific.com'})}).encode()
    _, data = get(op, 'https://platform.cloud.coveo.com/rest/search/v2?organizationId=bostonscientificproductionfv9tfxih',
                  body, {'Authorization': 'Bearer ' + token.group(1), 'Origin': 'https://www.bostonscientific.com',
                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    res = json.loads(data)
    print(f'Boston Scientific library ({args.country}), "{args.query}": {res.get("totalCount", 0)} results')
    for r in res.get('results', []):
        raw = r.get('raw', {})
        try:
            dates = {k: v for c in json.loads(raw.get('bsci_countrypublishdate', '{}'))['countriesWithPublishDates']
                     for k, v in c.items()}
        except (ValueError, KeyError, TypeError):
            dates = {}
        local = dates.get(args.country)
        markets = ', '.join(sorted(dates)) if len(dates) <= 12 else f'{len(dates)} markets'
        print(f'- {r.get("title", "")[:100]}\n  {r.get("clickUri", "")}\n'
              f'  published for {args.country}: {local or "no"}; markets: {markets}')


def biotronik(args):
    base = 'https://manuals.biotronik.com/emanuals-professionals/'
    op = opener()
    hdr = {'X-Requested-With': 'XMLHttpRequest', 'Referer': base, 'Accept': 'application/json'}

    def get_json(endpoint, params):
        _, body = get(op, base + endpoint + '?' + urllib.parse.urlencode(params), headers=hdr)
        try:
            return json.loads(body)
        except ValueError:  # errors arrive as HTTP 200 with an HTML page
            sys.exit(f'{endpoint}: unexpected response; the library may have changed.')

    devices = get_json('getDevices', {'query': args.product, 'country': args.country})
    want = args.product.strip().casefold()
    hits = [d for d in devices if d['title'].strip().casefold() == want] or \
           [d for d in devices if want in d['title'].casefold()]
    if len(hits) != 1:
        print(f'{len(hits)} products match "{args.product}" in {args.country}. Use the exact title:')
        for d in hits or devices[:30]:
            print(f'- {d["title"]}')
        return
    data = get_json('getManuals', {'country': args.country, 'id': hits[0]['id'],
                                   'allRev': 'true' if args.all else 'false', 'addlangs': ''})
    print(f'BIOTRONIK Manual Library ({args.country}), {hits[0]["title"]}: {len(data.get("data", []))} rows'
          + ('' if args.all else ' (current only; add --all for earlier revisions)'))
    for row in data.get('data', []):
        rev, mfile = row.get('revision') or {}, row.get('manualFile') or {}
        name = mfile.get('fileName') or ''
        m = re.match(r'([A-Za-z]*\d+)-([A-Za-z]{1,2})_(\d{2})-(\d{2})_', name)
        ident = f'{m.group(1)}-{m.group(2)} ({m.group(3)}/{m.group(4)})' if m else f'revision {rev.get("title")}'
        print(f'{"* " if rev.get("latest") else "  "}{ident} released {rev.get("releaseDate")} | {row.get("title")}'
              f'\n  {mfile.get("url")}')


def integra(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from integra_eifu import search_integra_eifu
    docs = search_integra_eifu(args.query, country=args.country, fetch_viewer=not args.fast)
    print(f'Integra eIFU ({args.country}), "{args.query}": {len(docs)} documents. Status comes from each '
          'document page: most_recent, out_of_date, or unmarked (no revision chain shown).')
    for d in docs:
        later = '; superseded by ' + ', '.join(x['label'] for x in d['superseded_by']) if d.get('superseded_by') else ''
        print(f'- {d["document_name"] or d["title"]} | part {d["part_number"]} Rev {d["revision"]} | '
              f'effective {d["effective_date"]} | {d["status"]}{later}\n  {d["pdf_url"] or d["viewer_url"]}')


def abbott(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from abbott_eifu import search_abbott_eifu
    docs = search_abbott_eifu(args.query, country=args.country, current_only=not args.all,
                              title_must_match=not args.loose)
    print(f'Abbott eIFU ({args.country}, healthcare professional), "{args.query}": {len(docs)} '
          f'{"documents" if args.all else "current documents"}'
          + ('' if args.loose else ' whose title contains every word (add --loose for the site\'s broad search)'))
    for d in docs[:40]:
        prev = f'; replaces {", ".join(d["replaces"])}' if d['replaces'] else ''
        end = f' to {d["effective_end"]}' if d.get('effective_end') else ''
        print(f'{"* " if d["current"] else "  "}{d["title"]} | {d["doc_number"]} {d["revision"] or ""} | '
              f'effective {d["effective_date"]}{end}{prev}\n  {d["pdf_url"]}')


def inspire(args):
    _, page = get(opener(), 'https://manuals.inspiresleep.com/')
    page = page.decode('utf-8', 'ignore')
    if 'English - US' not in page:
        print('Warning: could not confirm the English - US list; check the language on the portal.')
    rows = []
    for row in re.findall(r'<tr>(.*?)</tr>', page, flags=re.S):
        cells = [text(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S)]
        link = re.search(r'href="([^"]+manual\.php[^"]*)"', row)
        if len(cells) >= 4 and link and (not args.query or args.query.lower() in cells[0].lower()):
            rows.append((cells, 'https://manuals.inspiresleep.com' + link.group(1)))
    print(f'Inspire e-labeling, English - US list: {len(rows)} documents'
          + (f' matching "{args.query}"' if args.query else ''))
    for cells, url in rows:
        print(f'- {cells[0]} | {cells[1]} Rev {cells[2]} | {cells[3]}\n  {url}')


def redirect(args):
    final, _ = get(opener(), args.url)
    print(urllib.parse.unquote(final))


def fetch_pdf(url):
    cache = Path(tempfile.gettempdir()) / f'mrsa-{hashlib.sha1(url.encode()).hexdigest()[:16]}.pdf'
    if cache.exists():  # reuse the download across repeated calls for the same document
        return cache.read_bytes()
    # Some sites reject a browser User-Agent that cannot run JavaScript but accept a plain
    # download tool, and others need a browser one, so try both.
    for agent in (UA, 'Wget/1.21'):
        op = opener()
        op.addheaders = [('User-Agent', agent), ('Accept', '*/*')]
        try:
            _, data = get(op, url)
        except OSError:
            continue
        start = data.find(b'%PDF')
        if start >= 0:
            cache.write_bytes(data[start:])  # some servers wrap the file in a multipart body
            return data[start:]
    sys.exit('Could not download a PDF from this address. Try the host\'s own fetch or PDF tool.')


def pdf(args):
    gs = shutil.which('gs')
    if not gs:
        sys.exit('Ghostscript (gs) is not installed; use the host\'s PDF reader instead.')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'doc.pdf'
        src.write_bytes(fetch_pdf(args.url))
        subprocess.run([gs, '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=txtwrite',
                        f'-sOutputFile={tmp}/p%03d.txt', str(src)], check=True, capture_output=True)
        pages = [re.sub(r'\s+', ' ', p.read_text(encoding='utf-8', errors='ignore')).strip()
                 for p in sorted(Path(tmp).glob('p*.txt'))]
        print(f'{len(pages)} pages. Text extraction can drop spaces, superscripts, and table layout.')
        if pages:
            print(f'\n[page 1]\n{pages[0][:700]}\n\n[page {len(pages)}]\n{pages[-1][-700:]}')
            # Identity lines are often in the middle of a cover or back page, so list likely
            # document numbers, revisions, and dates from the first and last two pages.
            edge = ' '.join(pages[:2] + pages[-2:])
            ids = re.findall(r'\b(?:[A-Z]{1,6}[-_ ]?)?\d{5,}[A-Z0-9_\-]*(?:\s+(?:Rev\.?|REV|Rev)\s*[A-Z0-9]{1,3})?'
                             r'(?:\s+(?:EN|en)\s+\w+)?(?:\s+\d{4}[-/]\d{2}(?:[-/]\d{2})?)?', edge)
            dates = re.findall(r'\b(?:20\d\d[-/]\d\d(?:[-/]\d\d)?|\d\d/20\d\d|\d\d/\d\d)\b', edge)
            found = list(dict.fromkeys(x.strip() for x in ids + dates if len(x.strip()) > 4))[:15]
            if found:
                print('\nPossible identity strings (first and last two pages): ' + '; '.join(found))
            print(f'Identity lines can be missing from the text layer (rotated, upside down, or image text). '
                  f'If the document number and date are not clear above, render the covers with '
                  f'--render 1 --render {len(pages)} and read them.')
        for phrase in args.find or []:
            key = re.sub(r'\s+', '', phrase).lower()
            hits = [i + 1 for i, p in enumerate(pages) if key in re.sub(r'\s+', '', p).lower()]
            print(f'\n"{phrase}": pages {hits or "not found"}')
            for n in hits[:3]:
                flat, raw = re.sub(r'\s+', '', pages[n - 1]).lower(), pages[n - 1]
                at = flat.find(key)
                ratio = at / max(len(flat), 1)
                mid = int(ratio * len(raw))
                print(f'  p{n}: ...{raw[max(0, mid - 150):mid + 350]}...')
            if hits:
                print('  (snippets only; read whole pages with --text before relying on them)')
        for spec in args.text or []:
            first, _, last = spec.partition('-')
            for n in range(int(first), int(last or first) + 1):
                if 1 <= n <= len(pages):
                    print(f'\n[page {n}, full extracted text]\n{pages[n - 1]}')
        out = Path(args.out).resolve() if args.out else Path(tempfile.gettempdir()) / 'mrsa-pages'
        for n in args.render or []:
            out.mkdir(parents=True, exist_ok=True)
            png = out / f'page-{n}.png'
            subprocess.run([gs, '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=png16m', '-r110',
                            f'-dFirstPage={n}', f'-dLastPage={n}',
                            f'-sOutputFile={png}', str(src)], check=True, capture_output=True)
            print(f'\nRendered page {n}: {png}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('medtronic')
    g = m.add_mutually_exclusive_group(required=True)
    g.add_argument('--model')
    g.add_argument('--brand')
    m.add_argument('--library', choices=['mri', 'main'], default='mri')
    m.add_argument('--region', default='en_US')
    b = sub.add_parser('bsci')
    b.add_argument('query')
    b.add_argument('--country', default='us')
    b.add_argument('--count', type=int, default=15)
    bt = sub.add_parser('biotronik')
    bt.add_argument('product')
    bt.add_argument('--country', default='US')
    bt.add_argument('--all', action='store_true')
    ig = sub.add_parser('integra')
    ig.add_argument('query')
    ig.add_argument('--country', default='US')
    ig.add_argument('--fast', action='store_true', help='skip document pages (no PDF link or status)')
    ab = sub.add_parser('abbott')
    ab.add_argument('query')
    ab.add_argument('--country', default='US')
    ab.add_argument('--all', action='store_true', help='include superseded editions')
    ab.add_argument('--loose', action='store_true', help='return every hit, as the site does')
    i = sub.add_parser('inspire')
    i.add_argument('--query')
    r = sub.add_parser('redirect')
    r.add_argument('url')
    p = sub.add_parser('pdf')
    p.add_argument('url')
    p.add_argument('--find', action='append')
    p.add_argument('--text', action='append', help='print a page\'s full extracted text, e.g. 8 or 4-10; repeat for more')
    p.add_argument('--render', type=int, action='append', help='page to render as PNG; repeat for more pages')
    p.add_argument('--out', help='folder for rendered pages (default: a folder in the system temp directory)')
    args = ap.parse_args()
    {'medtronic': medtronic, 'bsci': bsci, 'biotronik': biotronik, 'integra': integra, 'abbott': abbott, 'inspire': inspire, 'redirect': redirect, 'pdf': pdf}[args.cmd](args)


if __name__ == '__main__':
    main()
