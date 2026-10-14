#!/usr/bin/env python3
"""Record the repository's GitHub star count and render light and dark SVG history charts.

GitHub lists individual stargazers only to repository admins, but the star count is public.
The website deploy workflow runs this daily: it appends the count to a CSV kept on the `stats`
branch when the count has changed, and publishes the charts with the site, so the README shows
the project's own logo instead of a third-party chart with the owner's avatar.

Usage:
  python scripts/star_history.py --record stats/star-history.csv --out _site/assets

Reads GITHUB_TOKEN if it is set. Python standard library only.
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
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


def get(path):
    req = urllib.request.Request(API + path, headers={'Accept': 'application/vnd.github+json',
                                                      'User-Agent': 'star-history-chart'})
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def day(text):
    return dt.datetime.fromisoformat(text[:10]).replace(tzinfo=dt.timezone.utc)


def read_history(path):
    if not path or not Path(path).exists():
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return [(day(r['date']), int(r['stars'])) for r in csv.DictReader(f) if r.get('date')]


def record(path, history, today, count):
    """Append today's count when it differs from the last recorded count. Returns True if written."""
    if history and history[-1][1] == count:
        return False
    if history and history[-1][0] == today:
        history[-1] = (today, count)
    else:
        history.append((today, count))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['date', 'stars'])
        w.writerows((d.strftime('%Y-%m-%d'), c) for d, c in history)
    return True


def nice_top(value):
    for exp in range(0, 9):
        for base in (1, 2, 5):
            step = base * 10 ** exp
            if math.ceil(max(value, 1) / step) <= 5:
                return step, step * math.ceil(max(value, 1) / step)
    return 10 ** 9, 10 ** 9


def render(repo, created, history, total, now, theme):
    """Draw the recorded counts as a step line from the repository's creation to now."""
    c = THEMES[theme]
    w, h = 800, 400
    left, right, top, bottom = 64, 28, 92, 56
    pw, ph = w - left - right, h - top - bottom
    step, ymax = nice_top(max([total] + [n for _, n in history]))
    start = min([created] + [d for d, _ in history[:1]])
    span = max((now - start).total_seconds(), 86400)
    x = lambda t: left + pw * min(max((t - start).total_seconds(), 0), span) / span
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
    if total or any(n for _, n in history):
        pts, count = [(x(start), y(0))], 0
        for d, n in history:
            pts.append((x(d), y(count)))
            count = n
            pts.append((x(d), y(count)))
        if count != total:
            pts += [(x(now), y(count)), (x(now), y(total))]
        pts.append((x(now), y(total)))
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
    ap.add_argument('--record', help='CSV of daily star counts to read and update')
    ap.add_argument('--out', default='web/assets', help='folder for star-history.svg and star-history-dark.svg')
    args = ap.parse_args()
    info = get(f'/repos/{args.repo}')
    total = int(info['stargazers_count'])
    now = dt.datetime.now(dt.timezone.utc)
    history = read_history(args.record)
    if args.record and record(args.record, history, day(now.isoformat()), total):
        print(f'Recorded {total} stars for {now:%Y-%m-%d} in {args.record}')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme, name in (('light', 'star-history.svg'), ('dark', 'star-history-dark.svg')):
        (out / name).write_text(render(args.repo, day(info['created_at']), history, total, now, theme), encoding='utf-8')
    print(f'{args.repo}: {total} stars; wrote {out}/star-history.svg and star-history-dark.svg')


if __name__ == '__main__':
    main()
