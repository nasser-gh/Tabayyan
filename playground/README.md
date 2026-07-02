# Tabayyan Playground

A lightweight, **fully-offline** web demo of [Tabayyan](https://pypi.org/project/tabayyan/).
Paste text, click **Scan**, and see Saudi PII detected, highlighted, classified,
and redacted — no code required.

> It's a demo, not a product. It's an **external consumer** of the library:
> it imports only the public API (`scan_and_redact`, `DetectionEngine`,
> `RedactionMode`) and duplicates no business logic. The core package is
> unchanged.

## Run it

```bash
# from the repo root
pip install -e .                      # the library (zero-dependency core)
pip install -r playground/requirements.txt
uvicorn playground.app:app --reload
# open http://127.0.0.1:8000
```

## What it shows

- **Two-column playground** — editor on the left, results on the right.
- **Detection** — highlighted entities (colored by category, hover for detector /
  confidence / category), plus a card per finding (name · value · confidence ·
  category · offsets).
- **Statistics** — totals by confidence, processing time, chars scanned, detectors run.
- **JSON view** — exactly what the API returns, with copy / download.
- **Redaction preview** — original → redacted (mask / remove / partial / hash /
  tokenize), with copy / download.
- **Samples** — realistic **synthetic** Arabic snippets (Healthcare, Banking,
  Government, HR, Support).
- **`.txt` upload / drag-and-drop**, character counter, clear, light/dark theme
  (remembered).

## Offline & privacy

Everything runs locally. **No** external APIs, CDNs, telemetry, or analytics.
Uploaded `.txt` files are read in the browser (`FileReader`) and never written
to disk. Styling and scripts are vendored locally (custom CSS + vanilla JS) so
the app works with the network disconnected.

> **Note on the stack:** the brief suggested HTMX + Tailwind (CDN). Because
> "completely offline / no external APIs" is a hard requirement and a Tailwind
> build step isn't part of this repo, the UI uses local custom CSS + vanilla
> `fetch` instead — same behaviour, zero external requests.

## Built to extend

The app is a thin presentation layer over the public API, so future additions
(PDF/DOCX extraction, OCR, batch scanning, an audit viewer) slot in as new
routes/inputs without touching the core library. Only text (`.txt`) is
supported today — by design.
