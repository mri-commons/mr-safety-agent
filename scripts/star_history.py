#!/usr/bin/env python3
"""Render the repository's GitHub star history as light and dark SVG charts.

The website deploy workflow runs this and publishes the charts with the site, so the README
shows the project's own logo instead of a third-party chart with the owner's avatar.

Usage:
  python scripts/star_history.py --repo mri-commons/mr-safety-agent --out _site/assets

Reads GITHUB_TOKEN if it is set. Python standard library only.
"""
import argparse
import datetime as dt
import json
import math
import os
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

API = 'https://api.github.com'
LOGO = ('<path d="M48 17 L82 29 L82 51 C82 72 65 84 48 91 C31 84 14 72 14 51 L14 29 Z" fill="#255be6"/>'
        '<line x1="48" y1="17" x2="48" y2="8" stroke="#255be6" stroke-width="5"/>'
        '<circle cx="48" cy="7" r="5" fill="#255be6"/>'
        '<rect x="24" y="34" width="48" height="32" rx="13" fill="#ffffff"/>'
        '<line x1="34" y1="49" x2="34" y2="54" stroke="#255be6" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="62" y1="49" x2="62" y2="54" stroke="#255be6" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M42 58 Q48 63 54 58" fill="none" stroke="#255be6" stroke-width="4" stroke-linecap="round"/>')
THEMES = {
    'light': {'bg': '#ffffff', 'border': '#e0e7f0', 'ink': '#132442', 'muted': '#5b6a81',
              'grid': '#edf1f7', 'line': '#255be6'},
    'dark': {'bg': '#0d1117', 'border': '#30363d', 'ink': '#e6edf3', 'muted': '#8b949e',
             'grid': '#21262d', 'line': '#4f8cff'},
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def get(path, accept='application/vnd.github+json'):
    req = urllib.request.Request(API + path, headers={'Accept': accept, 'User-Agent': 'star-history-chart'})
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def when(stamp):
    return dt.datetime.fromisoformat(stamp.replace('Z', '+00:00'))


def star_times(repo, max_pages=100):
    times = []
    for page in range(1, max_pages + 1):
        batch = get(f'/repos/{repo}/stargazers?per_page=100&page={page}', 'application/vnd.github.star+json')
        times += [when(s['starred_at']) for s in batch if s.get('starred_at')]
        if len(batch) < 100:
            break
    return sorted(times)


def nice_top(value):
    for exp in range(0, 9):
        for base in (1, 2, 5):
            step = base * 10 ** exp
            if math.ceil(max(value, 1) / step) <= 5:
                return step, step * math.ceil(max(value, 1) / step)
    return 10 ** 9, 10 ** 9


def render(repo, created, times, now, theme, total=None):
    c = THEMES[theme]
    w, h = 800, 400
    left, right, top, bottom = 64, 28, 92, 56
    pw, ph = w - left - right, h - top - bottom
    known = total is None or total == len(times)
    total = len(times) if total is None else total
    step, ymax = nice_top(total)
    start = min([created] + times[:1])
    span = max((now - start).total_seconds(), 86400)
    x = lambda t: left + pw * (t - start).total_seconds() / span
    y = lambda v: top + ph * (1 - v / ymax)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="GitHub star history for {escape(repo)}: {total} stars">',
           f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{c["bg"]}" stroke="{c["border"]}"/>',
           f'<g transform="translate(28 22) scale(0.42)">{LOGO}</g>',
           f'<text x="76" y="44" font-family="{FONT}" font-size="20" font-weight="700" fill="{c["ink"]}">MR Safety Agent</text>',
           f'<text x="76" y="65" font-family="{FONT}" font-size="13" fill="{c["muted"]}">GitHub stars · {escape(repo)}</text>',
           f'<text x="{w - 28}" y="50" text-anchor="end" font-family="{FONT}" font-size="28" font-weight="700" fill="{c["line"]}">{total:,}</text>',
           f'<text x="{w - 28}" y="68" text-anchor="end" font-family="{FONT}" font-size="12" fill="{c["muted"]}">{"star" if total == 1 else "stars"}</text>']
    for v in range(0, ymax + 1, step):
        yy = y(v)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{w - right}" y2="{yy:.1f}" stroke="{c["grid"]}"/>')
        out.append(f'<text x="{left - 10}" y="{yy + 4:.1f}" text-anchor="end" font-family="{FONT}" font-size="12" fill="{c["muted"]}">{v:,}</text>')
    fmt = '%b %d' if span <= 120 * 86400 else '%b %Y'
    seen = set()
    for i in range(5):
        t = start + dt.timedelta(seconds=span * i / 4)
        label = t.strftime(fmt).replace(' 0', ' ')
        if label in seen:
            continue
        seen.add(label)
        out.append(f'<text x="{x(t):.1f}" y="{h - bottom + 22}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{c["muted"]}">{label}</text>')
    if not known:
        out.append(f'<text x="{left + pw / 2:.1f}" y="{top + ph / 2:.1f}" text-anchor="middle" font-family="{FONT}" font-size="16" fill="{c["muted"]}">History unavailable</text>')
    elif total:
        pts, count = [(x(start), y(0))], 0
        for t in times:
            pts.append((x(t), y(count)))
            count += 1
            pts.append((x(t), y(count)))
        pts.append((x(now), y(count)))
        line = ' '.join(f'{px:.1f},{py:.1f}' for px, py in pts)
        area = f'{line} {x(now):.1f},{y(0):.1f} {x(start):.1f},{y(0):.1f}'
        out.append(f'<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["line"]}" stop-opacity="0.22"/>'
                   f'<stop offset="1" stop-color="{c["line"]}" stop-opacity="0"/></linearGradient></defs>')
        out.append(f'<polygon points="{area}" fill="url(#fill)"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="{c["line"]}" stroke-width="2.5" stroke-linejoin="round"/>')
    else:
        out.append(f'<line x1="{left}" y1="{y(0):.1f}" x2="{w - right}" y2="{y(0):.1f}" stroke="{c["line"]}" stroke-width="2.5"/>')
        out.append(f'<text x="{left + pw / 2:.1f}" y="{top + ph / 2:.1f}" text-anchor="middle" font-family="{FONT}" font-size="16" fill="{c["muted"]}">No stars yet</text>')
    out.append(f'<text x="{w - 28}" y="{h - 14}" text-anchor="end" font-family="{FONT}" font-size="11" fill="{c["muted"]}">Updated {now:%Y-%m-%d}</text>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', 'mri-commons/mr-safety-agent'))
    ap.add_argument('--out', default='web/assets', help='folder for star-history.svg and star-history-dark.svg')
    args = ap.parse_args()
    info = get(f'/repos/{args.repo}')
    try:
        times, total = star_times(args.repo), None
    except urllib.error.HTTPError as exc:  # GitHub lists stargazers only to repository admins
        print(f'Could not list stargazers ({exc.code}); showing the total only.')
        times, total = [], info['stargazers_count']
    now = dt.datetime.now(dt.timezone.utc)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme, name in (('light', 'star-history.svg'), ('dark', 'star-history-dark.svg')):
        (out / name).write_text(render(args.repo, when(info['created_at']), times, now, theme, total), encoding='utf-8')
    print(f'{args.repo}: {len(times) if total is None else total} stars; wrote {out}/star-history.svg and star-history-dark.svg')


if __name__ == '__main__':
    main()
