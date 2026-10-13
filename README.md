<div align="center">

<img src="assets/logo.svg" width="104" alt="MR Safety Agent logo: a blue shield with a friendly robot face">

# MR Safety Agent

**MRI Safety Research for Implants, Devices, and MR Safety Questions, With Each Claim Tied to a Source It Opened.**

<a href="https://mri-commons.github.io/mr-safety-agent/"><img src="assets/open-website-button.svg" width="420" alt="Open the website: mri-commons.github.io/mr-safety-agent"></a>

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-255BE6)](skills/mr-safety-agent/SKILL.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-255BE6)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-compatible-255BE6)](https://agentskills.io)
[![Scope](https://img.shields.io/badge/scope-US--first-255BE6)](#scope-and-limits)

[Install](#install) · [With and without the skill](#same-ai-with-and-without-the-skill) · [Website](https://mri-commons.github.io/mr-safety-agent/) · [Feedback](#feedback) · [Contributing](CONTRIBUTING.md)

</div>

> [!IMPORTANT]
> MR Safety Agent is research support, not scan clearance, and it has not been clinically validated. It does not interpret images or prescribe scanner settings. Each MR safety decision stays with the facility's MRMD and MR safety team. Never enter patient identifiers. Device details are all it needs.

MR Safety Agent is an open-source [Agent Skill](https://agentskills.io): a set of instructions and source routes that teaches an AI assistant to research MR safety the way a careful MR safety officer would. One package is designed for Claude, ChatGPT, and Gemini products that support skills.

## What It Does

| | Task | What You Get |
| :---: | --- | --- |
| 📄 | **Device MRI Labeling** | The applicable manufacturer manual, matched to the exact model, market, and revision, with safety notices checked, conditions cited by page, and gaps listed. |
| 🧲 | **MR Safety Questions** | Answers grounded in ACR, FDA, and other primary sources, including MRI suite emergencies, in plain language for patients and families or in depth for the MR safety team. |
| 🎓 | **US Certification** | MRSO, MRSE, MRMD, and MRST pathways from the credentialing body, with course certificates, credentials, and job roles kept distinct, and study plans built from the current exam syllabus. |

## Same AI, With and Without the Skill

Two examples, each the same question asked of the same model with and without the skill:

| Question | Without the Skill | With MR Safety Agent |
| --- | --- | --- |
| ACCOLADE MRI L311 pacemaker with INGEVITY MRI 7741/7742 leads: what are the current US 3 T conditions? | Found the current US guide and its 3 T conditions, but missed the May 2026 FDA Class I correction listing the L311, a Safety Mode risk | Same guide, each condition cited by page; found the FDA correction and flagged Safety Mode status to confirm |
| Abbott Proclaim XR SCS with two 3228 leads: what does the current US manual say for a 3 T lumbar MRI? | Right conclusion (1.5 T only), but read an older third-party copy and offered its outdated limits as the stricter option | Used the current official manual (December 2025) and documented which edition it replaced |

## Who It's For

| If You Are… | Use It To… |
| --- | --- |
| **A Patient or Family Member** | Learn what device information the imaging team needs and what to ask, in plain language. |
| **An MR Technologist or MR Safety Officer** | Find the right manual and revision, get page-cited conditions, and see what still needs checking before the scan. |
| **A Radiologist or Referring Physician** | Review the evidence behind a device's MR labeling and the open questions. |
| **A Student or Learner** | Understand MR safety concepts and plan US certification from the exam syllabus. |

### Built to Catch What Is Easy to Miss

- **Wrong Edition.** It reads each document's own identity line, so a European manual or a superseded revision is not passed off as current US labeling.
- **Safety Notices.** It looks for FDA and manufacturer notices that affect the device and opens them before judging whether they apply.
- **Tables and Footnotes.** It reads the conditions pages in full and checks table values on the rendered page.
- **Over-Generalizing.** One system's conditions are never applied to another system, lead, or field strength.
- **Honest Gaps.** It lists only the sources it actually opened and labels what it could not verify.

## Install

> [!NOTE]
> Menus change. If a step differs, follow your tool's current documentation.

**Chat Apps (Claude, ChatGPT, Gemini)**

1. **Download** [`mr-safety-agent.zip`](https://mri-commons.github.io/mr-safety-agent/assets/mr-safety-agent.zip) from the [website](https://mri-commons.github.io/mr-safety-agent/).
2. **Upload** it to your app:

   | App | Where to Upload (October 2026) |
   | --- | --- |
   | Claude (web, desktop, mobile) | Turn on **Settings → Capabilities → Code execution and file creation**, then upload in **Customize → Skills**. |
   | ChatGPT | Paid plans, including Plus, Pro, Business, Enterprise, Healthcare, and Edu: **Plugins → Skills → Create → Upload from your computer**. Uploaded skills work only in **Work**, not in regular chat. Enterprise and Edu admins may need to enable skills. |
   | Gemini | Skills began rolling out in October 2026. When **Skills** appears, upload the zip. |

3. **Make Sure the Skill Is Turned On**, then ask normally or name it. In ChatGPT, use it in **Work**.

**Coding Agents** such as Claude Code, Codex, and Gemini CLI. One command with the [skills CLI](https://github.com/vercel-labs/skills) (requires Node.js; add `-g` to install for all projects):

```sh
npx skills add mri-commons/mr-safety-agent --skill mr-safety-agent
```

<details>
<summary><b>More Options: Claude Code Plugin, ChatGPT and Codex Plugin, Manual Copy, and Tools Without Skills</b></summary>

**Claude Code Plugin**

```sh
claude plugin marketplace add mri-commons/mr-safety-agent
claude plugin install mr-safety-agent@mr-safety-agent
```

**ChatGPT and Codex Plugin.** Add the marketplace, then install **MR Safety Agent** from the Codex plugin browser. The portable manifest is [`plugin.json`](plugin.json). The plugin is not yet listed in the shared Plugin Directory.

```sh
codex plugin marketplace add mri-commons/mr-safety-agent
```

**Manual Copy.** Place `skills/mr-safety-agent` in `~/.claude/skills/` (Claude Code), `.agents/skills/` (Codex), or `~/.gemini/skills/` (Gemini CLI). Do not overwrite an existing skill with the same name.

**Tools Without Skill Support**, such as the free ChatGPT plan: create a project or custom assistant, add `SKILL.md` and the files in `references/`, and instruct it to follow `SKILL.md`. This approximates the skill, but the AI may consult the reference files less reliably.

**Telemetry.** The skills CLI reports installs to its maintainers. See its documentation.

</details>

## Examples

Give exact model numbers for device questions. For example:

```text
Find the current US MRI technical guide for a Boston Scientific ACCOLADE MRI
L311 pacemaker with INGEVITY MRI 7741 and 7742 leads, and list its 3 T conditions.

My father has a Medtronic pacemaker from around 2018. Can he have a 3 T MRI
tomorrow? Give me a yes or no.

According to the current ACR Manual on MR Safety, who controls access to Zone III?
```

A professional answer leads with the finding and its source, then lists what remains unknown, the safety notices checked, and the sources opened. A patient or family member gets a short answer instead: what is unresolved, what to find (usually the implant card), and whom to call.

## Website

A static companion site lets anyone use the project without installing an AI tool:

- **Guides**: twenty-seven guides in six groups: cardiac devices, neuromodulation, hearing implants, diabetes devices, shunt valves, and breast tissue expanders. They cover Medtronic, Abbott, Boston Scientific, BIOTRONIK, Nevro, LivaNova, Inspire, Cochlear, MED-EL, Advanced Bionics, Dexcom, MiniMed, Insulet, Tandem, Integra, Aesculap, Sophysa, AbbVie, Mentor, Sientra, and Establishment Labs. Each guide explains where the manufacturer publishes MRI documents, how to find the current US edition, how to confirm it, and the traps to avoid.
- **Key References**: ACR, FDA, RadiologyInfo, and IBMRS pages, plus cross-check tools such as AccessGUDID and FDA's recall list.
- **Skill Download and Install Options.**

<img src="assets/readme-website.png" alt="The website's guides, grouped into cardiac devices, neuromodulation, hearing implants, diabetes devices, shunt valves, and breast tissue expanders">

Open it at **<https://mri-commons.github.io/mr-safety-agent/>**. To preview a local copy, follow the development setup in [CONTRIBUTING.md](CONTRIBUTING.md); `scripts/dev.py` serves it with live reload. Guide content lives in [`content/guides/`](content/guides/).

## How It Works

The AI reads only the workflow it needs. A [source directory](skills/mr-safety-agent/references/sources.json) gives curated starting points and verified notes on how each manufacturer's library finds the current revision. Every current claim must come from a source opened during the task, and the answer lists only the sources actually opened. The package has no model, hosted service, or clinical integration. Search and PDF reading come from your AI tool.

## Scope and Limits

- **US-First.** Other regions need their own applicable sources.
- **Not a Database.** The directory lists starting points, not stored device labels. Manuals are linked, not redistributed.
- **Tool-Dependent.** As of October 2026, behavior has been evaluated in Claude Code, with limited testing in ChatGPT Work. Other hosts are untested.
- **Privacy.** Do not enter patient names, dates of birth, or record numbers. Use device details only.

## Feedback

Every comment, correction, and suggestion is welcome. [Open an issue](https://github.com/mri-commons/mr-safety-agent/issues/new) to report a wrong or outdated source, a misleading answer, or an idea. Leave out patient information.

## Contributing

Corrections, new sources, and regional proposals are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers source rules, quality checks, and development setup.

## License

Original project materials are under the [MIT License](LICENSE). Third-party publications, device manuals, trademarks, and linked content keep their own terms. No affiliation with or endorsement by any listed organization is claimed.

MR Safety Agent is part of [MRI Commons](https://github.com/mri-commons), a home for open MRI projects.

## Star History

<a href="https://www.star-history.com/#mri-commons/mr-safety-agent&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=mri-commons/mr-safety-agent&type=Date&theme=dark">
    <img alt="Star history chart for mri-commons/mr-safety-agent" src="https://api.star-history.com/svg?repos=mri-commons/mr-safety-agent&type=Date">
  </picture>
</a>
