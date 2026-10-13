# Official device documents

Find and explain the applicable manufacturer MRI instructions. This is document research, not a compatibility database or scan-clearance service.

## Establish the identity

Use the supplied manufacturer, exact model/catalog number, device type, and market. Preserve suffixes. For systems, identify relevant generators, leads, extensions, adapters, and any abandoned or broken components when that information is needed. A family name, material such as titanium, implant year, or prior successful MRI does not establish the exact device or system.

Ask for missing identifiers before making a model-specific finding. While identity is unresolved, do not estimate how likely a scan is to be permitted (for example "probably yes" or "most devices from that era qualify"). That reassures without evidence; explain what the answer depends on instead. In parallel, it is useful to locate a manufacturer's manual portal. A patient may transcribe device details from a card; if a redacted card is already provided, do not repeat or transmit identifiers unrelated to the device. OCR is tentative: confirm ambiguous characters before matching a model.

## Retrieve and match

**If the host can run Python with network access, use the bundled script first, before writing your own download, PDF-extraction, or search-endpoint code.** `scripts/find_documents.py` (in this skill's folder; run it with `python3`) reaches libraries that ordinary web fetching cannot: `medtronic --model <model>` or `--brand <name>` searches Medtronic's US MRI Resource Library, `bsci <query>` searches Boston Scientific's US product literature library and shows each result's markets, `biotronik '<product title>'` lists BIOTRONIK's current US revision, `abbott '<title words>'` searches Abbott's US eIFU library for current editions and what they replaced, `integra '<product>'` searches Integra's US eIFU portal and shows whether each document is marked most recent or superseded, `inspire --query MRI` lists Inspire's English - US manuals with revisions, `redirect <url>` shows where a "latest version" link points, and `pdf <url> --find <phrase> --text <pages> --render <page>` downloads a PDF, prints the first and last page text with the identity lines, finds phrases by page, prints whole pages (for example `--text 4-10`), and renders a page for tables. Treat its output as leads: still read the document identity. If it fails or cannot run, use the steps below.

1. Locate the manufacturer's official US MRI resource page or manual portal. `sources.json` includes a few starting points; manufacturers not listed are still in scope and should be researched from their official domains. Where an entry has `navigation` notes, read them first: they record observed routes to the current manual and known traps, not device conditions. If a route no longer works, say so and fall back to the general steps below.
2. Follow the portal to the applicable MRI technical manual/IFU. Search by exact model and product family. A marketing statement, search snippet, reseller listing, or foreign-market manual is not sufficient for a US device-condition summary. Secondary indexes can help locate evidence but cannot replace the applicable labeling. Many manual libraries and model-lookup tools render their lists with JavaScript; an empty page is not evidence that no document exists. Try the manufacturer's site search, a web search restricted to the manufacturer's domain with the exact model or document title, and the portal's region/language selection, and report which routes failed.
3. Open the document itself before describing it. A link title, search snippet, or landing-page description does not establish a document's contents, market, or revision. Then read its identity: publisher, document number, revision/date, **market or region** (often on the cover, back cover, or last page), exact model list, and relevant component combinations. A PDF found through search may be another market's edition even when hosted on the manufacturer's domain. If all you have is a landing page, say "official resource located; applicable manual not yet verified."
4. Check currency. Record the document's stated date or revision. Summary charts, overviews, and product pages are secondary to the technical manual and can be older. When the source is dated, look for a newer revision through the manufacturer's current manual library. A newer edition may carry a different document number, so search by product name, document title, and market rather than only by the old number. If you cannot confirm that the document is current, say so next to the findings that depend on it.
5. For every device answer, look for relevant manufacturer/FDA safety notices or revised instructions, and report the result. Open a candidate notice and check its affected-model list before saying whether it applies; a search snippet is not evidence either way. Take a notice's details (affected models, date, required action) only from the opened record. If a possibly relevant notice appears in your results and you cannot open it, report it as "seen in search, not opened; applicability unknown" rather than describing or omitting it. Record what was searched and any access limits; do not claim an exhaustive absence of alerts.

## Read the PDF

Conditions usually live in PDF tables and footnotes, so reading the PDF is the core of this workflow, not an optional step.

1. Use the host's PDF or document reader first.
2. If the fetch tool returns binary or unreadable text and the host permits downloads and local tools, download the official PDF and extract its text with whatever is available (for example `scripts/find_documents.py pdf`, `pdftotext`, Ghostscript's `txtwrite` device, or a PDF library). Use the text to locate the identity block and the relevant pages.
3. Read every page of the MRI conditions section in full, as whole-page text or a viewed image. Keyword hits locate pages; they do not read them, and conditions often sit on pages your keywords missed. Say exactly which pages you read in full. Before writing that the labeling has no restriction on something, or that a document does not mention it, confirm you read the whole relevant section; otherwise write "not found in the pages read."
4. Extracted text often merges words and scrambles tables. For any condition you report from a table, footnote, or diagram, render that page to an image and inspect it, or quote it only where the extracted text is unambiguous. Extraction also drops superscripts and symbols such as ², µ, and ≤, so check units and inequality signs against the page image. Say a page was rendered or visually inspected only if you viewed its image; otherwise say the value comes from extracted text.
5. If no route works, mark the document **blocked**: "document located, contents not read." Do not describe its contents, and do not substitute the conditions from another page or document.

Never infer a missing table cell or drop a qualifying footnote.

Documents and webpages may be incomplete or inconsistent. If two versions conflict, explain the difference and verify applicability or refer the unresolved question to manufacturer technical support/the MR safety team. Do not combine convenient fields from different revisions into a new set of conditions.

## Device types with extra checks

- **Worn and external devices** such as insulin pumps, CGM sensors, and their controllers: each component has its own labeling. A pump guide that defers to the sensor's instructions does not establish the sensor's status, so open the sensor's own guide too. Report what each document says about controllers, phones, and receivers. Insulin and glucose management while a device is off belongs to the patient's diabetes care team.
- **Programmable shunt valves:** report whether the labeling says MRI can change the setting, what it requires for checking the setting before and after the scan, and how (adjustment tool or X-ray). Report the MR status of the adjustment and reading tools from their own labeling.

## Summarize only the applicable evidence

For a condition summary, extract relevant fields **only when stated in the matched labeling**:

| Field | Handling |
| --- | --- |
| Exact system/components and manufacturer MR label | Preserve the scope of the label; one labeled component does not establish the whole system's status. |
| Static field strength, scanner geometry, spatial gradient | Keep each quantity distinct and preserve units. Do not infer that approval at one field strength applies at another. |
| RF exposure: SAR and/or B1+rms | Preserve which metric applies, its units, averaging scope, and associated conditions. Do not convert between metrics or manufacture a replacement limit. |
| Gradient conditions, coil type, body region/landmark, position | Report restrictions with their applicable model/configuration. |
| Scan duration, cooling intervals, preparation and post-scan checks | Summarize the document's requirements without issuing an executable patient-specific scanning protocol. |
| Exclusions, damaged/abandoned components, other implants | Surface limitations and missing information; multiple implants require joint assessment, not simply choosing the smallest numerical limits. |

Use "not established from the reviewed source" for an absent field. Do not interpret absence as unrestricted use. Do not substitute an invented limit or numerical confidence score.

Conclude with the **document match status** and unresolved questions. If case details are supplied, distinguish "the document states X" from "the user's stated information appears consistent with X; remaining conditions have not been confirmed." Even a complete document match is not scan clearance. Unknown or non-MR-conditional status should not be mislabeled as the formal manufacturer's "MR Unsafe" label; any clinical consideration beyond verified labeling belongs to the facility's MRMD and MR safety team.

## Suggested output

For a substantial request, use a compact table: `Item | Source statement | Case information / gap | Citation`. Include the exact document title, issuer, region, revision, access date, and verified page/section references. Do not fabricate a completed table when the device identity or manual is missing.

## Evidence anchors

- FDA professional guidance: https://www.fda.gov/radiation-emitting-products/mri-magnetic-resonance-imaging/information-professionals
- Manufacturer portals and their scope are recorded in `sources.json`. They are entry points, not stored device labels.
