#!/usr/bin/env python3
"""Validate the package's structural contracts; never claim clinical correctness."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


def validate(root: Path) -> list[str]:
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def read_json(path):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
            require(isinstance(result, dict), f"{path.name}: expected an object")
            return result if isinstance(result, dict) else {}
        except (OSError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")
            return {}

    def checked_date(value, context):
        try:
            parsed = date.fromisoformat(value)
            require(parsed.isoformat() == value, f"{context}: use YYYY-MM-DD")
            require(parsed <= date.today(), f"{context}: date is in the future")
        except (ValueError, TypeError):
            errors.append(f"{context}: expected a valid YYYY-MM-DD date")

    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())

    skill = root / "skills/mr-safety-agent"
    try:
        content = (skill / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", content, re.S)
        require(match is not None, "SKILL.md: missing YAML frontmatter")
        if match:
            meta = yaml.safe_load(match.group(1))
            require(isinstance(meta, dict), "SKILL.md: metadata must be a mapping")
            if isinstance(meta, dict):
                require(meta.get("name") == skill.name, "SKILL.md: name must match its folder")
                description = meta.get("description")
                # 200 is the strictest host limit observed (Claude apps); the open standard allows 1024.
                require(nonempty(description) and len(description) <= 200,
                        "SKILL.md: description must contain 1-200 characters")
        require("[TODO:" not in content, "SKILL.md: unfinished scaffold")
        ui = yaml.safe_load((skill / "agents/openai.yaml").read_text(encoding="utf-8"))
        interface = ui.get("interface", {}) if isinstance(ui, dict) else {}
        require(isinstance(interface, dict), "openai.yaml: interface must be a mapping")
        if isinstance(interface, dict):
            require(nonempty(interface.get("display_name")), "openai.yaml: missing display name")
            short = interface.get("short_description", "")
            require(isinstance(short, str) and 25 <= len(short) <= 64,
                    "openai.yaml: short description must be 25-64 characters")
            prompt = interface.get("default_prompt", "")
            require(isinstance(prompt, str) and "$mr-safety-agent" in prompt,
                    "openai.yaml: default prompt must invoke the skill")
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"Skill metadata: {exc}")

    registry = read_json(skill / "references/sources.json")
    require(registry.get("schema_version") == 1, "sources: unsupported schema version")
    require(registry.get("default_jurisdiction") == "US", "sources: expected US default")
    require(nonempty(registry.get("verification_note")), "sources: missing verification definition")
    sources = registry.get("sources", [])
    require(isinstance(sources, list) and bool(sources), "sources: expected nonempty list")
    ids, urls = set(), set()
    kinds = {"regulator", "professional-guidance", "patient-education",
             "credentialing-body", "manufacturer-portal"}
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict):
            errors.append("sources: each entry must be an object")
            continue
        sid = source.get("id")
        if not nonempty(sid):
            errors.append("sources: missing string id")
            continue
        require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", sid)), f"{sid}: invalid id")
        require(sid not in ids, f"{sid}: duplicate source id")
        ids.add(sid)
        for field in ("title", "publisher", "url", "jurisdiction", "scope"):
            require(nonempty(source.get(field)), f"{sid}: missing {field}")
        url = source.get("url", "")
        if isinstance(url, str):
            try:
                parts = urlsplit(url)
                require(parts.scheme == "https" and bool(parts.hostname) and not parts.username,
                        f"{sid}: expected public HTTPS source URL")
            except ValueError:
                errors.append(f"{sid}: malformed URL")
            require(url not in urls, f"{sid}: duplicate source URL")
            urls.add(url)
        kind = source.get("kind")
        require(isinstance(kind, str) and kind in kinds, f"{sid}: unknown source kind")
        topics = source.get("topics")
        require(isinstance(topics, list) and bool(topics) and all(nonempty(t) for t in topics),
                f"{sid}: topics must be a nonempty string list")
        if "navigation" in source:
            navigation = source["navigation"]
            require(isinstance(navigation, list) and bool(navigation)
                    and all(nonempty(n) for n in navigation),
                    f"{sid}: navigation must be a nonempty string list")
        checked_date(source.get("verified_on"), f"{sid}: verified_on")
        status = source.get("review_status")
        require(isinstance(status, str) and status in {"source-checked", "expert-reviewed"},
                f"{sid}: invalid review status")
        if status == "expert-reviewed":
            review = source.get("review", {})
            require(isinstance(review, dict), f"{sid}: review must be an object")
            if isinstance(review, dict):
                for field in ("reviewer", "credentials", "scope"):
                    require(nonempty(review.get(field)), f"{sid}: expert review missing {field}")
                checked_date(review.get("date"), f"{sid}: review date")

    # Behavioral evaluation cases are kept locally and are optional here.
    cases_path = root / "evals/cases.json"
    if cases_path.exists():
        evaluations = read_json(cases_path)
        require(evaluations.get("schema_version") == 1, "evals: unsupported schema version")
        cases = evaluations.get("cases", [])
        require(isinstance(cases, list) and bool(cases), "evals: expected nonempty case list")
        case_ids = set()
        for case in cases if isinstance(cases, list) else []:
            if not isinstance(case, dict) or not nonempty(case.get("id")):
                errors.append("evals: each case must have a string id")
                continue
            cid = case["id"]
            require(cid not in case_ids, f"{cid}: duplicate case id")
            case_ids.add(cid)
            mode = case.get("mode")
            require(isinstance(mode, str) and mode in {"live", "offline", "routing"}, f"{cid}: invalid mode")
            require(nonempty(case.get("prompt")), f"{cid}: missing prompt")
            for field in ("must_include", "must_not"):
                values = case.get(field)
                require(isinstance(values, list) and bool(values) and all(nonempty(v) for v in values),
                        f"{cid}: {field} must be a nonempty string list")
            source_ids = case.get("source_ids")
            require(isinstance(source_ids, list), f"{cid}: source_ids must be a list")
            for sid in source_ids if isinstance(source_ids, list) else []:
                require(isinstance(sid, str) and sid in ids, f"{cid}: unknown source id {sid}")

    # The repository uses simple inline Markdown links. External URLs and
    # fragment targets are excluded; this checks that bundled files resolve.
    markdown = list(root.glob("*.md")) + list(skill.rglob("*.md")) + list((root / "evals").rglob("*.md"))
    for path in markdown:
        if "local-runs" in path.parts:
            continue
        for target in re.findall(r"\[[^\]\n]+\]\(([^\s)]+)\)", path.read_text(encoding="utf-8")):
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0])
            destination = (path.parent / target).resolve()
            require(destination.is_relative_to(root.resolve()), f"{path.name}: link leaves repository: {target}")
            require(destination.exists(), f"{path.name}: broken local link: {target}")

    # Device document guides rendered into the website.
    guide_ids = set()
    for path in sorted((root / "content/guides").glob("*.yaml")):
        try:
            guide = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if not isinstance(guide, dict):
            errors.append(f"{path.name}: expected a mapping")
            continue
        gid = guide.get("id")
        require(gid == path.stem, f"{path.name}: id must match the file name")
        require(gid not in guide_ids, f"{path.name}: duplicate guide id")
        guide_ids.add(gid)
        for field in ("manufacturer", "category", "devices", "title", "covers", "summary"):
            require(nonempty(guide.get(field)), f"{path.name}: missing {field}")
        checked_date(guide.get("verified_on"), f"{path.name}: verified_on")
        for field in ("steps", "check", "traps"):
            values = guide.get(field)
            require(isinstance(values, list) and bool(values) and all(nonempty(v) for v in values),
                    f"{path.name}: {field} must be a nonempty string list")
        for field in ("where", "also"):
            links = guide.get(field) or []
            require(field != "where" or bool(links), f"{path.name}: where must list at least one link")
            for link in links if isinstance(links, list) else []:
                ok = isinstance(link, dict) and all(nonempty(link.get(k)) for k in ("label", "url", "note"))
                require(ok and urlsplit(link["url"]).scheme == "https",
                        f"{path.name}: {field} entries need label, note, and an https url")
        # Optional edition watch entries read by scripts/check_editions.py.
        watch_needs = {"pdf": ("url",), "page": ("url",), "redirect": ("url",), "medtronic": ("query",)}
        for entry in guide.get("watch") or []:
            kind = entry.get("type") if isinstance(entry, dict) else None
            ok = kind in watch_needs and nonempty(entry.get("document")) and nonempty(entry.get("expect"))
            ok = ok and all(nonempty(entry.get(k)) for k in watch_needs[kind])
            ok = ok and (kind == "medtronic" or urlsplit(entry["url"]).scheme == "https")
            require(ok, f"{path.name}: watch entries need document, expect, a known type, and its url or query")

    # Topic pages: every section must cite at least one declared source.
    for path in sorted((root / "content/topics").glob("*.yaml")):
        try:
            topic = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if not isinstance(topic, dict):
            errors.append(f"{path.name}: expected a mapping")
            continue
        require(topic.get("id") == path.stem, f"{path.name}: id must match the file name")
        for field in ("title", "audience", "summary", "note"):
            require(nonempty(topic.get(field)), f"{path.name}: missing {field}")
        checked_date(topic.get("verified_on"), f"{path.name}: verified_on")
        keys = set()
        for src in topic.get("sources") or []:
            ok = isinstance(src, dict) and all(nonempty(src.get(k)) for k in ("key", "label", "url"))
            require(ok and urlsplit(src["url"]).scheme == "https", f"{path.name}: sources need key, label, and an https url")
            if ok:
                keys.add(src["key"])
        about = bool(topic.get("about"))  # site pages such as the methodology page
        require(about or bool(keys), f"{path.name}: at least one source is required")
        sections = topic.get("sections")
        require(isinstance(sections, list) and bool(sections), f"{path.name}: sections must be a nonempty list")
        for sec in sections if isinstance(sections, list) else []:
            name = sec.get("heading") if isinstance(sec, dict) else None
            require(nonempty(name), f"{path.name}: every section needs a heading")
            if not isinstance(sec, dict):
                continue
            require(nonempty(sec.get("text")) or bool(sec.get("items")) or bool(sec.get("table")), f"{path.name}: {name}: needs text, items, or a table")
            cited = sec.get("sources") or []
            require((about and not cited) or (bool(cited) and all(k in keys for k in cited)),
                    f"{path.name}: {name}: cite declared sources")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("Structural validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Structural validation passed (metadata, local links, sources" + (", evaluation definitions" if (args.root / "evals/cases.json").exists() else "") + ").")
    print("No live source verification, model evaluation, or clinical validation was performed by this command.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
