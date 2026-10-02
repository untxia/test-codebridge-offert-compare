# Delivery notes — Offer Compare

Fields marked **[Chris]** must be filled in by the author before submitting (I can't know them).

## 1. Sample inputs (all fictional; `testset/pdf/`, `evaluation/holdout/`)
| Case | Pair | What it tests |
|---|---|---|
| S1 normal | offer_original → offer_revised | price, quantity, delivery, removal, stated total; rename + reorder; revised HT stated 19,060 but lines sum to 18,960 |
| S2 formatting only | original → original_reformatted | other fonts/colours, `1 150,00 €` → `EUR 1 150,00`, `16/11/2026` → `16 novembre 2026`, other headers: must report **nothing** |
| S3 ambiguous | original → revised_ambiguous | one line split in two (10×1150 → 6×1150 + 4×1290), rename-or-replacement, plus a clean qty change and total |
| S4 unreadable | original → revised_scanned | image-only PDF: must decline |
| H1/H2 hold-out | other vendor, English, USD, `1,150.00`, other column order, with/without grid | generalisation |

## 2. Expected vs actual (`python3 evaluation/evaluate.py`, 5 runs each)
| Scenario | Expected | Actual |
|---|---|---|
| S1 | conclude; 5 changes; 1 arithmetic discrepancy (100.00) | identical; net effect stated +160.00 vs recomputed +60.00 |
| S2 | no_changes | no_changes |
| S3 | partial; 2 confirmed (qty 4→5, stated total); 2 uncertain groups | identical; 560.00 left unattributed, shown |
| S4 | decline | decline (`no_text_layer_revised`) |
| H1, H2 | 6 changes each, 0 false | 6/6, 0 false (after the fixes in §4) |

Other formats: the S0→S1 pair also exists as xlsx, docx, ods, csv, html, md, txt and json (`testset/formats/`); `tests/test_formats.py` checks each gives exactly the PDF result and that mixed pairs (Excel vs Word, PDF vs Excel, JSON vs PDF) do too, with an Excel cell reference or table/row/line reference for each source. Same caveat: samples are mine.

Missed changes: **0/7** on S1–S4, **0/12** on hold-out (after fixes). False changes: **0**. Source references: 13/13 cite the expected page + line + label on both sides, and 13/13 bounding boxes contain the cited text/amount when re-read from the PDF independently (pdfplumber crop).
**Caveat:** I (with AI help) wrote both the samples and the answer keys. Zero errors on them says the pipeline is consistent, not that it works on arbitrary supplier PDFs. Real-world layouts are untested.

## 3. Time, speed, cost
* Time spent: **[Chris]** (ceiling 8 h). Work was split: test set + answer key, extraction, matching, diff/report, UI, evaluation, deploy/docs.
* Time to useful result: 50–75 ms per PDF extraction, 120–150 ms per pair end to end on the cloud sandbox (excluding upload); the page shows results immediately after "Compare".
* **Variable cost per document pair: 0 LLM tokens → 0 USD of model cost**, because the engine is deterministic (no model call at runtime). Remaining cost is compute only (~0.15 s CPU per pair) and is counted as hosting, kept separate (free-tier hosting is not claimed as "zero cost"). If an LLM were added for uncertain groups or scanned input, expect roughly one short call per uncertain group; not built, not measured.

## 4. What failed / was corrected (honest log)
* Hold-out run found **2 real defects** on first contact: a delivery date missed (header "Ship date", US `mm/dd/yyyy` dates) and totals "Subtotal / Total due" unrecognised. Fixed (header and total keywords, per-document date convention with a warning when ambiguous), then re-run.
* Tables without borders broke pdfplumber's text strategy → custom header-anchored word alignment; wrapped/vertically-centred labels then dropped a row → fragment re-attachment.
* My own verification script wrongly failed a long wrapped label → check switched to parsed row number + page + label.
* **Answer-key correction after seeing app output:** S3's key omitted the stated-total change; the app was right, the key was wrong. I added it as S3-C2 and changed the expected count 1→2. This weakens S3 as independent evidence; stated here deliberately.
* Not handled: scans (declined on purpose, no OCR), handwriting, multi-currency conversion, non-FR/EN labels, discounts/optional lines as separate semantics.

## 5. AI tools and models
Claude Code (Anthropic), model **Claude Sonnet 5.5** (`claude-sonnet-5-5`), used to write the code, test set, tests and documents under my direction. No AI model is called by the application at runtime. **[Chris]** add anything else you used.

## 6. One example of checking AI output
Running the app on S3 showed a stated-total change that my answer key lacked. I checked the two PDFs (18,900 → 19,640 is really there), concluded the key was wrong and the app right, corrected the key and disclosed it (§4), then re-ran the independent verifier (`verify_testset.py`). Another: bounding boxes are validated by re-reading the PDF text under each returned box, not by trusting the extractor.

## 7. Product judgement (20%)
* Certain vs uncertain is explicit: only unambiguous matches become changes; everything else is a question with the amount at stake, and the answer recomputes the report.
* The tool never "fixes" a document: stated vs recomputed totals are both shown.
* Declining is a first-class outcome with a reason, rather than a confident wrong table.
* Thresholds are constants and listed in the README so a reviewer can tighten or loosen them.
