# Contributing

Contribute a source correction, a workflow improvement, or a proposal for a new jurisdiction. Keep public content in English. Use fictional or de-identified examples and never include patient records or credentials.

## Sources and Evidence

The source registry is `skills/mr-safety-agent/references/sources.json`. Keep stable IDs, HTTPS URLs hosted by the publisher itself, explicit jurisdiction and scope, and the date you actually opened the page. A live page check does not establish that a PDF is the latest applicable revision or that its clinical interpretation is correct.

Use `review_status: source-checked` for a verified landing page. Mark an entry `expert-reviewed` only when a qualified reviewer has actually reviewed the stated scope, and add a `review` object with `reviewer`, `credentials`, `date`, and `scope`. Obtain permission before publishing a reviewer's identity. Review status does not imply organizational endorsement.

An optional `navigation` list records how to reach the current applicable document on that publisher's site: library routes, URL patterns that distinguish markets, how revisions are numbered, and known traps. Update `verified_on` when you re-check it. Do not add clinical thresholds or device labels to the navigation registry. For workflow changes involving clinical reasoning, include the relevant primary source, its revision/region, the specific section supporting the change, and an example question that shows the changed behavior. Do not copy third-party manuals into the repository unless redistribution is explicitly permitted and documented.

For updates, describe which tasks or findings are affected. If a source disappears, retain an honest record of the problem in the contribution discussion and propose a replacement hosted by the publisher; do not merely advance the check date. Routine version control records the edit history.

## Regional Contributions

The current supported scope is US-first. Propose another region with locally applicable sources, credentialing pathways, a named maintenance/review plan, and region-specific example questions. Translation alone does not establish that US instructions apply locally. Keep general principles separate from regional policy, labeling, and credential requirements.

## Quality Checks

Run `python scripts/validate.py` in the development environment below. For workflow changes, try the affected questions in a fresh session and include the actual response and tool record, not just a claim that it works.

Assess whether the cited source supports the claim, whether model/region/revision match, and whether missing evidence is acknowledged. A valid file format or an AI reviewer is not clinical validation. Before promoting safety guidance as clinically reviewed, obtain independent review by an appropriately qualified MR safety professional.

## Pull Request Contents

Explain the user problem, the resulting behavior, sources checked, validation performed, and remaining limitations. Separate proposed work from completed work. Report credential, privacy, and source errors without publishing secrets or patient information in public issues.

## Development Setup

The only dependency is PyYAML, listed in `requirements-dev.txt`. The commands below use a conda environment named `mr-safety-agent`. Without conda, uv works the same way: `uv run --with-requirements requirements-dev.txt python scripts/validate.py` (and the same for the other scripts).

The skill's own script, `skills/mr-safety-agent/scripts/find_documents.py`, needs only the Python standard library.

```sh
conda create -n mr-safety-agent -c conda-forge python=3.12 pyyaml   # once
conda run -n mr-safety-agent python scripts/validate.py   # structure, links, and sources
conda run -n mr-safety-agent python scripts/check_links.py # every external link still opens (needs network)
conda run -n mr-safety-agent python scripts/check_editions.py # each guide's documents are still the current editions (needs network)
conda run -n mr-safety-agent python scripts/dev.py        # website preview with live reload at http://127.0.0.1:8765/
```

The validator does not assess medical accuracy or test AI behavior. The live preview rebuilds the website's copies of the skill, source directory, and this guide when they change, runs the validator on every save, and shows failures as a banner. Run `python3 web/build.py` to refresh those copies and the skill zip without the preview.

Repository Layout:

```text
skills/mr-safety-agent/   The skill: SKILL.md, workflows, source directory, icons
content/guides/           Device document guides (YAML), rendered into web/guides by build.py
web/                      Static website and build script
scripts/                  Validator, link and edition checkers, and live-reload preview server
plugin.json               Portable plugin manifest (Agent Plugins)
.claude-plugin/           Claude Code plugin marketplace
.agents/plugins/          Codex plugin marketplace
assets/                   Logo, app icons, and README images
```
