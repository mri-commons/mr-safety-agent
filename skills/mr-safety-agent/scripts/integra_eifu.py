"""Search Integra LifeSciences' eIFU portal (labeling.integralife.com/eifu/).

Standard library only. See search_integra_eifu() for details.
"""
import html
import http.cookiejar
import json
import re
import urllib.parse
import urllib.request

BASE = "https://labeling.integralife.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
_NOT_OBSOLETE = "((obsolete_md:false) OR (-obsolete_md:[* TO *]))"


def search_integra_eifu(query, country="US", user_type="provider",
                        fetch_viewer=True, timeout=30, max_pages=20):
    """Search the Integra eIFU portal by product name and return documents.

    How it works (mirrors the portal's "Product Name" search, no JS needed):
      1. Session: GET /eifu/ (server sets JSESSIONID + AWS ALB cookies), then
         set the cookies the landing page's JS would set: td.country, td.lang.
         No token is involved. td.country is REQUIRED by the autocomplete
         endpoint (it returns [] without it) and scopes its suggestions.
      2. Product names: the portal's Product Name search is an exact facet
         match, so the free-text query is resolved to the portal's exact
         productName values. Sources (unioned):
           a) GET /eifu/pages/autocomplete?key=productName&query=<word>
              (JSON list, ISO-8859-1 encoded; one call per query word, since
              multi-word queries return []), and
           b) the product facet sidebar of a full-text search
              GET /eifu/search?searchMode=text&term=(w1 AND w2 ...)
              (UTF-8; used to repair autocomplete names where non-Latin-1
              characters such as the trademark sign came back as '?').
         A name is kept if every query word is a prefix of some word in it
         (case-insensitive, (R)/(TM) symbols ignored).
      3. Documents: GET /eifu/search?searchMode=productName with one
         f.productName_md=<name> per matched name (OR'ed by the server),
         f.country_md=<country>, f.userType_md=<user_type>. Results are
         server-rendered HTML, 10 per page; pages fetched via &page=N
         (0-based) until all "Showing a - b of N results" are collected.
      4. Per document (if fetch_viewer): GET the viewer page
         /eifu/pages/viewers/pdf?projectKey=..&itemKey=.. which holds the
         PDF path and the "Most recent." / "Out of date." banner with
         Supersedes / Superseded by links.

    Args:
        query: product name words, e.g. "CERTAS Plus" or "HAKIM".
        country: portal country code (default "US"); sent as f.country_md
            (this is what filters results) and as the td.country cookie.
        user_type: "provider" (portal default, IFUs), "patient" (patient
            information leaflets), or None for both.
        fetch_viewer: fetch each viewer page for pdf_url and status.
        timeout: per-request timeout in seconds.
        max_pages: safety cap on result pages.

    Returns:
        list of dicts with keys: title (file name heading), document_name,
        product, part_number, revision, reference_numbers, languages,
        effective_date (YYYY-MM-DD string as shown), status ("most_recent",
        "out_of_date", "unmarked" = viewer has no revision banner, None =
        viewer not fetched), status_text (banner text as shown),
        supersedes / superseded_by (lists of {"label", "viewer_url"}),
        pdf_url, viewer_url, project_key, item_key, metadata (all raw
        label -> value pairs). Ordered as the portal sorts them
        (effective date, descending, per page).
    """
    words = [w for w in re.findall(r"\w+", _norm(query)) if w]
    if not words:
        raise ValueError("query must contain at least one word")

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA),
                         ("Accept-Language", "en-US,en;q=0.9")]

    def get(path, params=None):
        url = path if path.startswith("http") else BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        with opener.open(url, timeout=timeout) as r:
            raw = r.read()
            charset = r.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, "replace")

    # 1. session + country/language cookies
    get("/eifu/")
    for name, value in (("td.country", country), ("td.lang", "en")):
        jar.set_cookie(http.cookiejar.Cookie(
            0, name, value, None, False, "labeling.integralife.com", False,
            False, "/eifu/", True, True, None, False, None, None, {}))

    common = [("f.country_md", country), ("maxFacetValues", "100"),
              ("sortBy", "effective_md"), ("sortDirection", "DESC")]
    if user_type:
        common.append(("f.userType_md", user_type))

    # 2. resolve query -> exact product names
    auto = []
    for w in dict.fromkeys(words):
        txt = get("/eifu/pages/autocomplete",
                  [("key", "productName"), ("query", w)]).strip()
        auto.extend(json.loads(txt) if txt else [])
    text_term = "(%s) AND %s" % (" AND ".join(words), _NOT_OBSOLETE)
    page = get("/eifu/search", [("term", text_term), ("searchMode", "text"),
                                ("query", query), ("formattedSearch", query)]
               + common)
    facets = [html.unescape(v) for v in re.findall(
        r'name="f\.productName_md"\s+value="([^"]*)"', page)]
    names = []
    for n in facets + auto:
        if "?" in n:  # autocomplete lost a non-Latin-1 char; repair via facets
            pat = re.compile("^" + ".".join(map(re.escape, n.split("?"))) + "$")
            n = next((f for f in facets if pat.match(f)), n)
        if n not in names and _matches(words, n):
            names.append(n)
    if not names:
        return []

    # 3. product-name facet search, paginated
    params = ([("term", "(*) AND " + _NOT_OBSOLETE), ("searchMode", "productName"),
               ("query", query), ("formattedSearch", "*")] + common
              + [("f.productName_md", n) for n in names])
    docs, seen = [], set()
    for pg in range(max_pages):
        page = get("/eifu/search", params + ([("page", str(pg))] if pg else []))
        entries = page.split('class="searchResultEntry')[1:]
        new = [d for d in map(_parse_entry, entries) if d["item_key"] not in seen]
        for d in new:
            seen.add(d["item_key"])
        docs.extend(new)
        m = re.search(r"Showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)", page)
        if not new or not m or len(docs) >= int(m.group(1)):
            break

    # 4. viewer page: PDF link + most-recent / superseded banner
    if fetch_viewer:
        for d in docs:
            d.update(_parse_viewer(get(d["viewer_url"])))
    return docs


def _norm(s):
    s = s.replace("®", " ").replace("™", " ").replace("?", " ")
    return re.sub(r"\s+", " ", s).strip().casefold()


def _matches(words, name):
    name_words = re.findall(r"\w+", _norm(name))
    return all(any(nw.startswith(w) for nw in name_words) for w in words)


def _clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def _parse_entry(block):
    meta = {_clean(k): _clean(v) for k, v in re.findall(
        r"<label>(.*?)</label>\s*</div>\s*<div[^>]*>(.*?)</div>", block, re.S)}
    title = re.search(r"<h4>(.*?)</h4>", block, re.S)
    viewer = re.search(r'href="(/eifu/pages/viewers/pdf\?[^"]+)"', block)
    viewer_url = BASE + html.unescape(viewer.group(1)) if viewer else None
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(viewer_url or "").query)
    refs = meta.get("Reference Number (SKU)")
    return {
        "title": _clean(title.group(1)) if title else None,
        "document_name": meta.get("Document Name"),
        "product": meta.get("Product"),
        "part_number": meta.get("Part Number"),
        "revision": meta.get("Revision"),
        "reference_numbers": [r.strip() for r in refs.split(",")] if refs else [],
        "languages": meta.get("Language(s)"),
        "effective_date": meta.get("Effective date"),
        "status": None, "status_text": None,
        "supersedes": [], "superseded_by": [],
        "pdf_url": None,
        "viewer_url": viewer_url,
        "project_key": (q.get("projectKey") or [None])[0],
        "item_key": (q.get("itemKey") or [None])[0],
        "metadata": meta,
    }


def _parse_viewer(page):
    out = {"status": "unmarked"}  # viewer shows no revision banner at all
    m = re.search(r'<a href="([^"]+)"[^>]*>\s*Open in new tab', page) or \
        re.search(r'<iframe[^>]*src="([^"#]+)', page)
    if m:
        path = html.unescape(m.group(1))
        out["pdf_url"] = urllib.parse.urljoin(
            BASE, urllib.parse.quote(path, safe="/"))
    m = re.search(r'class="alert alert-\w+ revLink"[^>]*>\s*([^<]*?)\s*<', page)
    if m:
        text = m.group(1).strip()
        out["status_text"] = text
        low = text.lower()
        out["status"] = ("most_recent" if "most recent" in low else
                         "out_of_date" if "out of date" in low else "other")
    for key, cls in (("supersedes", "supersedes"), ("superseded_by", "supersededBy")):
        out[key] = [{"label": _clean(lbl), "viewer_url": BASE + html.unescape(href)}
                    for href, lbl in re.findall(
                        r'class="revLink %s">[^<]*<a href="([^"]+)">(.*?)</a>' % cls,
                        page, re.S)]
    return out


if __name__ == "__main__":
    import sys
    for q in sys.argv[1:] or ["CERTAS Plus", "HAKIM"]:
        print("=" * 20, q)
        print(json.dumps(search_integra_eifu(q), indent=1, ensure_ascii=False))
