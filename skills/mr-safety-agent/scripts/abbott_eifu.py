"""Search Abbott's eIFU manual library (https://manuals.eifu.abbott) - stdlib only."""
import datetime as _dt
import json
import re
import urllib.parse
import urllib.request

_SEARCH_URL = "https://services.abbott/api/public/search/sitesearch"
_BASE = "https://manuals.eifu.abbott"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")


def _parse_date(s):
    """Parse the library's mixed date formats ('19-Jan-2026', '18-OCT-16', ISO) -> date or None."""
    if not s:
        return None
    s = s.strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return _dt.date(int(m[1]), int(m[2]), int(m[3]))
    for fmt in ("%d-%b-%Y", "%d-%b-%y"):
        try:
            return _dt.datetime.strptime(s.title(), fmt).date()
        except ValueError:
            pass
    return None


def _doc_and_rev(url, title):
    """Split the PDF file name into (document number, revision)."""
    stem = urllib.parse.unquote(url.rsplit("/", 1)[-1]).rsplit(".", 1)[0]
    m = re.fullmatch(r"([A-Z]+\d+)_([A-Z0-9]*)", stem, re.I)       # ARTEN600340310_A, ART100119760_
    if m:
        return m[1].upper(), (m[2].upper() or None)
    m = re.search(r"([A-Z]{2,}\d{5,}(?:-\d+)?(?:-[A-Z]{2})?)", stem, re.I)  # vascular: EL2155005-EN Artwork
    doc = m[1].upper() if m else stem
    r = (re.search(r"(?<![A-Za-z])Rev\.?\s*([A-Z0-9]{1,3})\b", stem + " " + (title or ""), re.I)
         or re.search(r"_([A-Z])$", stem))
    return doc, (r[1].upper() if r else None)


def search_abbott_eifu(query, country="US", language="en", hcp=True,
                       current_only=True, title_must_match=False, today=None, timeout=60):
    """Search Abbott's eIFU library (manuals.eifu.abbott) like the site's search page does.

    Calls the same public JSON endpoint the site's JavaScript uses
    (GET https://services.abbott/api/public/search/sitesearch) with the headers the page
    embeds as hidden inputs (x-application-id=manualseifu, x-country-code, x-preferred-language).
    No token, cookie or session is needed. The site's client-side filtering is reproduced:
    keep only documents tagged for <country>/<language>/<hcp|nhcp>, and (if current_only) only
    those whose effective date range contains `today`, de-duplicated by (title, PDF URL).

    Args:
        query: free-text query (sent as-is; the backend ranks by relevance and is very
            permissive, so many loosely related documents come back, exactly as on the site).
        country, language: library tag, e.g. "US", "en" (country set to United States by default).
        hcp: True = healthcare-professional view (what the site shows after "Yes, I am an HCP");
            False = patient/lay view.
        current_only: True mimics the site (hides superseded/removed editions); False also
            returns superseded editions, with their effective_end date.
        title_must_match: False mimics the site (which lists every hit, mostly loosely related).
            True keeps only documents whose title contains every query word
            (case-insensitive; punctuation, hyphens and trademark signs ignored).
        today: datetime.date used for the current/superseded decision (default: local today).
        timeout: HTTP timeout in seconds.

    Returns:
        list of dicts in backend relevance order, each with keys:
        title, doc_number (e.g. "ARTEN600340310"), revision (e.g. "A" or None),
        effective_date (ISO "YYYY-MM-DD", from effectivebegindate, else ontime),
        effective_end (ISO or None; removal date if the library records one),
        replaces (list of earlier editions recorded in 'previousversions', e.g.
        ["ARTEN600343196_A"]; empty if not recorded), current (bool),
        pdf_url (absolute URL), categories (library product-category paths it is filed under).

    Raises:
        RuntimeError if the API reports an error; urllib.error.URLError on network errors.
    """
    today = today or _dt.date.today()
    filters = [{"tags": f"{country}/{language}", "role": "" if hcp else "NHCP"}]
    params = {
        "firstresult": 1, "q": query, "autocorrect": "false",
        "numberofresults": "",  # empty = return every hit in one response (as the site does)
        "searchtype": "sitesearch", "sort": "[]",
        "filters": json.dumps(filters, separators=(",", ":")),
    }
    req = urllib.request.Request(
        _SEARCH_URL + "?" + urllib.parse.urlencode(params),
        headers={
            "User-Agent": _UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": _BASE, "Referer": _BASE + "/",
            "x-application-id": "manualseifu",  # required (HTTP 400 without it)
            "x-country-code": country,          # required (HTTP 400 without it)
            "x-preferred-language": language,
        })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    if data.get("errorCode") != 0 or not data.get("status", True):
        raise RuntimeError(f"Abbott search API error: {str(data)[:300]}")

    want = f"/{country}/{language}/{'hcp' if hcp else 'nhcp'}/".lower()
    norm = lambda t: re.sub(r"[\W_]+", " ", t.lower()).split()
    q_words = norm(query)
    results = data.get("response", {}).get("results", [])
    # Vascular documents carry no effective dates; the site keeps only the newest ('ontime')
    # document per product page, so superseded vascular revisions are dropped that way.
    newest_vascular = {}
    for r in results:
        if "/vascular/" in (r.get("url") or ""):
            for p in re.findall(r"av:manualseifu/[^,]*", r.get("productname") or ""):
                if want in p.lower() + "/":
                    newest_vascular[p] = max(newest_vascular.get(p, ""), r.get("ontime") or "")
    out, seen = [], set()
    for r in results:
        url = r.get("url") or ""
        # productname = "Name1::av:manualseifu/US/en/hcp/<path>,Name2::<path2>,..." (one per tag)
        pairs = re.findall(r"(?:^|,)(.*?)::(av:manualseifu/[^,]*)", r.get("productname") or "", re.S)
        pairs = [(n, p) for n, p in pairs if want in p.lower() + "/"]
        title = " ".join((r.get("title") or r.get("systitle") or (pairs[0][0] if pairs else "")).split())
        paths = [p for _, p in pairs]
        if not paths or not url or not r.get("role") or not (r.get("category") or "").strip():
            continue
        begin = _parse_date(r.get("effectivebegindate")) or _parse_date(r.get("ontime"))
        end = _parse_date(r.get("removeddate")) or _parse_date(r.get("effectiveenddate"))
        current = (begin is None or begin <= today) and (end is None or end > today)
        if "/vascular/" in url:
            current = any((r.get("ontime") or "") >= newest_vascular.get(p, "") for p in paths)
        if current_only and not current:
            continue
        if title_must_match and not all(w in norm(title) for w in q_words):
            continue
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        doc, rev = _doc_and_rev(url, title)
        out.append({
            "title": title,
            "doc_number": doc,
            "revision": rev,
            "effective_date": begin.isoformat() if begin else None,
            "effective_end": end.isoformat() if end else None,
            "replaces": [v.strip() for v in re.split(r"[\r\n]+", r.get("previousversions") or "")
                         if v.strip()],
            "current": current,
            "pdf_url": urllib.parse.urljoin(_BASE, urllib.parse.quote(url, safe="/:")),
            "categories": sorted({p.split("/", 4)[-1].rsplit("/", 1)[0] for p in paths}),
        })
    return out


def unwrap_pdf(body):
    """Some PDFs are served wrapped in a multipart/form-data body; return the bare %PDF bytes."""
    start = body.find(b"%PDF-")
    end = body.rfind(b"%%EOF")
    if start < 0:
        raise ValueError("no PDF found in response body")
    return body[start:end + 5] if end > start else body[start:]
