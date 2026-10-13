"""Refresh the static preview from the project's shared sources, guides, and skill."""
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
import json
import shutil
import zipfile

import yaml

web = Path(__file__).resolve().parent
root = web.parent
skill = root / 'skills/mr-safety-agent'
guides_dir = root / 'content/guides'
(web / 'data').mkdir(exist_ok=True)
(web / 'assets').mkdir(exist_ok=True)
shutil.copyfile(skill / 'references/sources.json', web / 'data/sources.json')
shutil.copyfile(root / 'CONTRIBUTING.md', web / 'assets/CONTRIBUTING.md')
with zipfile.ZipFile(web / 'assets/mr-safety-agent.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(skill.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name != '.DS_Store':
            archive.write(path, Path('mr-safety-agent') / path.relative_to(skill))
    archive.write(root / 'LICENSE', 'mr-safety-agent/LICENSE')

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — MR Safety Agent</title>
  <meta name="description" content="{summary}">
  <link rel="icon" type="image/svg+xml" href="../assets/mr-safety-agent-logo.svg">
  <link rel="stylesheet" href="../style.css">
</head>
<body class="guide-page">
  <a class="skip" href="#gather">Skip to steps</a>
  <header><div class="nav wrap">
    <a class="brand" href="../index.html"><img class="brand-mark" src="../assets/mr-safety-agent-logo.svg" alt="" width="40" height="40"><span><b>MR Safety</b> Agent</span></a>
    <nav aria-label="Main navigation"><a href="../index.html#topics">Learn</a><a href="../index.html#guides">Guides</a><a href="../index.html#resources">References</a><a href="../index.html#agent">Use the Agent</a></nav>
  </div></header>
  <main>
    <section class="guide-hero"><div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="../index.html#guides">Guides</a><span aria-hidden="true">/</span><span>{manufacturer}</span></nav>
      <div class="guide-title"><span class="maker-mark" aria-hidden="true">{initials}</span><div><div class="eyebrow">GUIDE</div><h1>{title}</h1></div></div>
      <p class="guide-summary">{summary}</p>
      <ul class="chips"><li><b>Category</b> {category}</li><li><b>Covers</b> {covers}</li></ul>
    </div></section>
    <div class="guide-layout wrap">
      <article class="guide-main">
        <section class="guide-section" id="gather"><div class="phase">Step 1 of {total}</div><h2>Gather Model Numbers</h2><p class="phase-text">{gather}</p></section>
        <section class="guide-section" id="find"><div class="phase">Step 2 of {total}</div><h2>Find the Document</h2><div class="link-cards">{where}</div><ol class="steps">{steps}</ol></section>
        <section class="guide-section" id="confirm"><div class="phase">Step 3 of {total}</div><h2>Confirm It</h2>
          <div class="guide-pair">
            <div class="card-panel check"><h3><span aria-hidden="true">✓</span> Check the Document</h3><ul>{check}</ul></div>
            <div class="card-panel trap"><h3><span aria-hidden="true">!</span> Watch For</h3><ul>{traps}</ul></div>
          </div>
        </section>
        {also}
        <aside class="guide-note" role="note"><strong>Where to Look, Not Whether to Scan.</strong> This guide explains where {manufacturer} publishes MRI documents and how to confirm you have the right one. It does not state scan conditions or decide whether a patient can be scanned. Read the applicable document in full and follow your MR safety team's procedures. Manufacturer sites and documents change, so always confirm the edition on the document itself.</aside>
      </article>
      <aside class="guide-side" aria-label="On this page">
        <nav class="side-box toc" aria-label="On this page"><div class="eyebrow">ON THIS PAGE</div><a href="#gather">Gather Model Numbers</a><a href="#find">Find the Document</a><a href="#confirm">Confirm It</a>{also_link}</nav>
        <div class="side-box ask"><div class="eyebrow">RESEARCH WITH AI</div><p>Give the agent the exact model numbers. It finds the document, checks its identity, and lists what remains unverified.</p><p class="side-prompt">{prompt}</p><a class="text-link" href="../index.html#agent">Get the Agent <span>→</span></a></div>
      </aside>
    </div>
  </main>
  <footer><div class="wrap footer-bottom"><p>For research and education. Individual MRI decisions belong with the facility's MRMD and MR safety team. Links go to the publishers' own sites. No affiliation or endorsement is implied.</p><a href="../topics/how-we-check-sources.html">How We Check Sources</a><a href="../index.html">Back to MR Safety Agent →</a></div></footer>
  <script>(()=>{{const links=[...document.querySelectorAll('.toc a')];const items=links.map(a=>[a,document.querySelector(a.getAttribute('href'))]).filter(x=>x[1]);let lock=0,idle;const set=link=>links.forEach(a=>a.classList.toggle('active',a===link));const update=()=>{{if(Date.now()<lock)return;const line=Math.min(innerHeight*0.35,320);let cur=items[0],best=-Infinity;for(const it of items){{const top=it[1].getBoundingClientRect().top;if(top<=line&&top>best+1){{cur=it;best=top;}}}}if(innerHeight+scrollY>=document.documentElement.scrollHeight-4)cur=items[items.length-1];set(cur&&cur[0]);}};links.forEach(a=>a.addEventListener('click',()=>{{set(a);lock=Date.now()+1500;}}));addEventListener('scroll',()=>{{update();clearTimeout(idle);idle=setTimeout(()=>{{lock=0;}},180);}},{{passive:true}});addEventListener('resize',update);update();}})();</script>
</body>
</html>
"""


def link_card(item):
    host = urlsplit(item['url']).hostname.removeprefix('www.')
    return (f'<a class="link-card" href="{escape(item["url"])}" target="_blank" rel="noopener noreferrer">'
            f'<span class="link-label">{escape(item["label"])} <span aria-hidden="true">↗</span></span>'
            f'<span class="link-note">{escape(item["note"])}</span><span class="link-host">{escape(host)}</span></a>')


def items(values):
    return ''.join(f'<li>{escape(v)}</li>' for v in values)


def initials(name):
    words = [w for w in name.replace('-', ' ').split() if w[0].isalnum()]
    return ''.join(w[0] for w in words[:2]).upper()


guide_out = web / 'guides'
guide_out.mkdir(exist_ok=True)  # overwrite in place so concurrent builds (dev.py) cannot collide
index = []
for path in sorted(guides_dir.glob('*.yaml')):
    g = yaml.safe_load(path.read_text(encoding='utf-8'))
    also = g.get('also') or []
    parts = {'Diabetes Devices': '[pump, sensor, and app or controller]', 'Shunt Valves': '[valve model and catalog number]', 'Breast Tissue Expanders': '[expander model and port type]'}.get(g['category'], '[device and lead model numbers]')
    prompt = f'Find the current US MRI document for this {g["manufacturer"]} system: {parts}. Confirm its edition and list what is still unverified.'
    page = PAGE.format(
        title=escape(g['title']), summary=escape(g['summary']), manufacturer=escape(g['manufacturer']),
        initials=escape(initials(g['manufacturer'])), category=escape(g['category']), covers=escape(g['covers']), checked=escape(g['verified_on']),
        where=''.join(link_card(i) for i in g['where']), gather=escape(g['steps'][0]), steps=items(g['steps'][1:]),
        check=items(g['check']), total=4 if also else 3,
        traps=items(g['traps']), prompt=escape(prompt),
        also=(f'<section class="guide-section" id="also"><div class="phase">Step 4 of 4</div><h2>Check Notices and Related Pages</h2><div class="link-cards">{"".join(link_card(i) for i in also)}</div></section>' if also else ''),
        also_link=('<a href="#also">Check Notices and Related Pages</a>' if also else ''))
    (guide_out / f'{g["id"]}.html').write_text(page, encoding='utf-8')
    index.append({'id': g['id'], 'order': g.get('order', 99), 'category': g['category'], 'manufacturer': g['manufacturer'], 'devices': g['devices'], 'title': g['title'],
                  'covers': g['covers'], 'verified_on': g['verified_on'], 'initials': initials(g['manufacturer']),
                  'url': f'guides/{g["id"]}.html'})
index.sort(key=lambda g: (g['order'], g['manufacturer']))
for stale in set(guide_out.glob('*.html')) - {guide_out / f"{g['id']}.html" for g in index}:
    stale.unlink(missing_ok=True)
(web / 'data/guides.json').write_text(json.dumps({'guides': index}, indent=2) + '\n', encoding='utf-8')

TOPIC = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — MR Safety Agent</title>
  <meta name="description" content="{summary}">
  <link rel="icon" type="image/svg+xml" href="../assets/mr-safety-agent-logo.svg">
  <link rel="stylesheet" href="../style.css">
</head>
<body class="guide-page topic-page">
  <a class="skip" href="#content">Skip to content</a>
  <header><div class="nav wrap">
    <a class="brand" href="../index.html"><img class="brand-mark" src="../assets/mr-safety-agent-logo.svg" alt="" width="40" height="40"><span><b>MR Safety</b> Agent</span></a>
    <nav aria-label="Main navigation"><a href="../index.html#topics">Learn</a><a href="../index.html#guides">Guides</a><a href="../index.html#resources">References</a><a href="../index.html#agent">Use the Agent</a></nav>
  </div></header>
  <main>
    <section class="guide-hero"><div class="wrap">
      <nav class="crumbs" aria-label="Breadcrumb">{crumb}<span aria-hidden="true">/</span><span>{audience}</span></nav>
      <div class="eyebrow">{audience_upper}</div>
      <h1 class="topic-title">{title}</h1>
      <p class="guide-summary">{summary}</p>
      {chips}
    </div></section>
    <div class="guide-layout wrap" id="content">
      <article class="guide-main">
        {sections}
        <aside class="guide-note" role="note"><strong>{note_title}</strong> {note}</aside>
        {sources_block}
      </article>
      <aside class="guide-side" aria-label="On this page"><nav class="side-box toc" aria-label="On this page"><div class="eyebrow">ON THIS PAGE</div>{toc}{sources_link}</nav></aside>
    </div>
  </main>
  <footer><div class="wrap footer-bottom"><p>For research and education. Individual MRI decisions belong with the facility's MRMD and MR safety team. Links go to the publishers' own sites. No affiliation or endorsement is implied.</p><a href="how-we-check-sources.html">How We Check Sources</a><a href="../index.html">Back to MR Safety Agent →</a></div></footer>
  <script>(()=>{{const links=[...document.querySelectorAll('.toc a')];const items=links.map(a=>[a,document.querySelector(a.getAttribute('href'))]).filter(x=>x[1]);let lock=0,idle;const set=link=>links.forEach(a=>a.classList.toggle('active',a===link));const update=()=>{{if(Date.now()<lock)return;const line=Math.min(innerHeight*0.35,320);let cur=items[0],best=-Infinity;for(const it of items){{const top=it[1].getBoundingClientRect().top;if(top<=line&&top>best+1){{cur=it;best=top;}}}}if(innerHeight+scrollY>=document.documentElement.scrollHeight-4)cur=items[items.length-1];set(cur&&cur[0]);}};links.forEach(a=>a.addEventListener('click',()=>{{set(a);lock=Date.now()+1500;}}));addEventListener('scroll',()=>{{update();clearTimeout(idle);idle=setTimeout(()=>{{lock=0;}},180);}},{{passive:true}});addEventListener('resize',update);update();}})();</script>
</body>
</html>
"""


def slug(text):
    return ''.join(c if c.isalnum() else '-' for c in text.lower()).strip('-').replace('--', '-')


topic_out = web / 'topics'
topic_out.mkdir(exist_ok=True)
topics, site_pages = [], []
for path in sorted((root / 'content/topics').glob('*.yaml')):
    t = yaml.safe_load(path.read_text(encoding='utf-8'))
    about = bool(t.get('about'))  # site pages such as the methodology page: no Learn card, sources optional
    number = {src['key']: i + 1 for i, src in enumerate(t.get('sources') or [])}
    parts, toc = [], []
    for sec in t['sections']:
        sid = slug(sec['heading'])
        toc.append(f'<a href="#{sid}">{escape(sec["heading"])}</a>')
        body = f'<p>{escape(sec["text"])}</p>' if sec.get('text') else ''
        if sec.get('table'):
            head = ''.join(f'<th scope="col">{escape(c)}</th>' for c in sec['table']['columns'])
            cols = sec['table']['columns']
            rows = ''.join('<tr>' + ''.join((f'<th scope="row">{escape(c)}</th>' if j == 0 else
                                             f'<td data-label="{escape(cols[j]) if j < len(cols) else ""}">{escape(c)}</td>')
                                            for j, c in enumerate(r)) + '</tr>' for r in sec['table']['rows'])
            body += f'<div class="table-wrap"><table class="topic-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        if sec.get('items'):
            body += f'<ul class="topic-list">{items(sec["items"])}</ul>'
        if sec.get('after'):
            body += f'<p>{escape(sec["after"])}</p>'
        if sec.get('tip'):
            body += f'<p class="topic-tip"><b>Tip</b> {escape(sec["tip"])}</p>'
        refs = ', '.join(f'<a href="#src-{number[k]}">{number[k]}</a>' for k in sec.get('sources', []))
        cite = f'<p class="cite">Sources: {refs}</p>' if refs else ''
        parts.append(f'<section class="guide-section topic-section" id="{sid}"><h2>{escape(sec["heading"])}</h2>{body}{cite}</section>')
    source_list = ''.join(
        f'<li id="src-{i + 1}"><a href="{escape(src["url"])}" target="_blank" rel="noopener noreferrer">{escape(src["label"])} ↗</a></li>'
        for i, src in enumerate(t.get('sources') or []))
    sources_block = (f'<section class="guide-section topic-sources" id="sources"><h2>Sources</h2><ol>{source_list}</ol>'
                     '<p class="checked-line">Sites change. Follow the links for the current wording.</p></section>') if source_list else ''
    page = TOPIC.format(title=escape(t['title']), summary=escape(t['summary']), audience=escape(t['audience']),
                        audience_upper=escape(t['audience'].upper()), checked=escape(t['verified_on']),
                        sections=''.join(parts), note=escape(t['note']), toc=''.join(toc),
                        sources_block=sources_block, sources_link='<a href="#sources">Sources</a>' if source_list else '',
                        crumb='<a href="../index.html">Home</a>' if about else '<a href="../index.html#topics">Learn</a>',
                        note_title='About This Page.' if about else 'For Education, Not a Decision.',
                        chips='' if about else f'<ul class="chips"><li><b>Topic</b> {escape(t["audience"])}</li></ul>')
    (topic_out / f'{t["id"]}.html').write_text(page, encoding='utf-8')
    if about:
        site_pages.append(t['id'])
        continue
    topics.append({'id': t['id'], 'order': t.get('order', 99), 'audience': t['audience'], 'title': t['title'],
                   'summary': t['summary'], 'verified_on': t['verified_on'], 'url': f'topics/{t["id"]}.html'})
topics.sort(key=lambda t: (t['order'], t['title']))
for stale in set(topic_out.glob('*.html')) - {topic_out / f"{i}.html" for i in [t['id'] for t in topics] + site_pages}:
    stale.unlink(missing_ok=True)
(web / 'data/topics.json').write_text(json.dumps({'topics': topics}, indent=2) + '\n', encoding='utf-8')

print(f'Static preview refreshed: source directory, {len(index)} device guides, {len(topics)} topics, skill download, contribution guide.')
