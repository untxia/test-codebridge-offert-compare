# Offer Compare — commercial offer comparison (AI-First Product Builder take-home)

**Live demo:** https://test-codebridge-offert-compare.vercel.app  
**Repo:** https://github.com/untxia/test-codebridge-offert-compare

Upload an original commercial offer and its revision (two text PDFs). The app lists the **substantive** changes
(scope, quantities, unit prices, totals, delivery dates), each with a clickable reference to **both** locations
(page, line, highlighted area in the PDF). No line item is retyped.

* Matches lines despite renaming and reordering (renames/reorders are shown, never reported as commercial changes).
* Separates **confirmed changes** from **uncertain matches** (split/merge, rename-or-replacement) that it asks you to settle; your answer recomputes the result.
* Recomputes totals deterministically (Decimal): qty × unit price, sum of lines, VAT, total incl. VAT. A stated total that disagrees with its own lines is **flagged, never silently corrected**.
* Declines to conclude when it should: scanned/no-text PDF, no recognisable line table, mixed or different currencies.
* Interface in French and English. Nothing is stored server-side (stateless API, temp files deleted).

## Run locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn server:app --port 8000      # http://localhost:8000
```
Use the four example links on the page (normal case, formatting only, ambiguous case, scanned document) or upload your own PDFs.
Dev extras (regenerate the test PDFs): `pip install -r requirements-dev.txt`.

CLI: `python3 -m offercompare compare original.pdf revised.pdf` (JSON report).

## Tests and evaluation

```bash
python3 -m unittest discover -s tests -t .      # 23 unit/integration tests
python3 testset/verify_testset.py               # independent check of the test PDFs against their answer key
python3 evaluation/evaluate.py                  # missed / false changes, source references, timing (writes evaluation/results.json)
python3 testset/generate_testset.py             # regenerate the 5 sample PDFs + expected_differences.json
python3 evaluation/holdout/make_holdout.py      # regenerate the hold-out pairs (other vendor, EN, USD, other column order)
```

## How it works (no LLM in the loop)

1. **Extraction** (`offercompare/extract.py`, pdfplumber): columns are recognised by header keywords (FR/EN), never by position; two strategies (ruled tables, then header-anchored word alignment for tables without borders); wrapped labels are re-attached; every row, cell and total keeps its page and bounding box. Numeric dates: day-first/month-first decided by the document itself, otherwise by currency, with a warning.
2. **Matching** (`match.py`): score = 0.55·label similarity + 0.35·terms (price/qty/date) + 0.10·position. A pair is confirmed only if the label is near-identical *or* renamed with a high global score, and in both cases with a clear margin over the runner-up. Plausible but unconfirmed pairs form connected groups → *uncertain* (one-to-one, split/merge, many-to-many); the rest are removed/added. Thresholds are constants at the top of the file.
3. **Diff and report** (`diff.py`): change list, arithmetic checks, net effect (stated vs recomputed, amount left unattributed by uncertain groups), decision: `conclude`, `no_changes`, `conclude_partially_and_ask`, `decline`.
4. **UI** (`public/`): vanilla JS, pdf.js (vendored in `public/vendor`, Apache-2.0) for the side-by-side viewer with highlights; all text inserted with `textContent`.

## Deploy (Vercel)

`vercel.json` + `requirements.txt` + `api/index.py` (FastAPI) + `public/` (static). `vercel --prod` from this folder, or import the GitHub repo in Vercel with the **Other** preset (the config is in `vercel.json`).

## Reused components / limits

pdfplumber (pdfminer.six), FastAPI, pdf.js, reportlab/Pillow (test data only). Everything else is written for this test.
Limits: text PDFs only (no OCR — scans are declined on purpose), FR/EN column and total labels, one currency per document, layouts tested on the included samples only (see `DELIVERY_NOTES.md`), 2 MB per file.
