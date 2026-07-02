"""Tabayyan Playground — a lightweight, fully-offline demo web UI.

It is an **external consumer** of Tabayyan: it imports only the public API
(`scan`, `scan_and_redact`, `DetectionEngine`, `RedactionMode`) and never
touches internal modules. No business logic is duplicated here — the app just
calls the library and presents the results.

Offline by construction: no external APIs, no telemetry, no analytics, no CDN
assets, and uploaded files are read client-side (never written to disk).

Run:  uvicorn playground.app:app --reload   (from the repo root)
"""
from __future__ import annotations

import html
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# --- public API only ---
from tabayyan import DetectionEngine, RedactionMode, __version__, scan_and_redact

from playground.samples import SAMPLES

BASE = Path(__file__).parent
app = FastAPI(title="Tabayyan Playground", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

_engine = DetectionEngine()
DETECTOR_COUNT = len(_engine.detectors)
REDACTION_MODES = [m.value for m in RedactionMode]
_DEMO_SALT = "tabayyan-playground-demo"  # so `hash` mode works in the demo

# Human-friendly labels for entity types (falls back to Title Case).
_DISPLAY = {
    "saudi_national_id": "Saudi National ID",
    "saudi_iqama": "Saudi Iqama",
    "saudi_iban": "Saudi IBAN",
    "saudi_cr": "Commercial Registration",
    "saudi_vat": "VAT / Tax Number",
    "saudi_mobile": "Saudi Mobile",
    "saudi_landline": "Saudi Landline",
    "saudi_passport": "Passport",
    "saudi_border_number": "Border / Visa Number",
    "saudi_national_address": "National Address",
    "saudi_unified_number": "Unified Number (700)",
    "medical_record_number": "Medical Record Number",
    "credit_card": "Credit Card",
    "email": "Email",
    "ip_address": "IP Address",
    "arabic_name": "Arabic Name",
    "suspicious_domain": "Suspicious Domain",
    "custom": "Custom",
}


def _display(entity_type: str) -> str:
    return _DISPLAY.get(entity_type, entity_type.replace("_", " ").title())


def _highlight(text: str, matches) -> str:
    """Escaped HTML with <mark> spans over detected entities (with tooltips)."""
    parts: list[str] = []
    cursor = 0
    for m in sorted(matches, key=lambda x: x.start):
        if m.start < cursor:  # defensive; engine resolves overlaps already
            continue
        parts.append(html.escape(text[cursor:m.start]))
        seg = html.escape(text[m.start:m.end])
        cat = m.category.value
        tip = f"{_display(m.entity_type.value)} · {m.confidence.value.upper()} · {cat.replace('_', ' ')}"
        parts.append(f'<mark class="ent ent-{cat}" title="{html.escape(tip, quote=True)}">{seg}</mark>')
        cursor = m.end
    parts.append(html.escape(text[cursor:]))
    return "".join(parts).replace("\n", "<br>")


class ScanReq(BaseModel):
    text: str = ""


class RedactReq(BaseModel):
    text: str = ""
    mode: str = "mask"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "samples": SAMPLES,
            "detector_count": DETECTOR_COUNT,
            "version": __version__,
            "python": "3.9 – 3.13",
            "modes": REDACTION_MODES,
        },
    )


@app.post("/api/scan")
def api_scan(req: ScanReq):
    text = req.text or ""
    try:
        t0 = time.perf_counter()
        matches = _engine.scan(text)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
    except Exception:  # never leak a traceback to the UI
        return JSONResponse({"error": "Something went wrong while scanning."}, status_code=400)

    conf = {"high": 0, "medium": 0, "low": 0}
    items = []
    for m in matches:
        conf[m.confidence.value] = conf.get(m.confidence.value, 0) + 1
        items.append({
            "detector": _display(m.entity_type.value),
            "type": m.entity_type.value,
            "value": m.value,
            "confidence": m.confidence.value,
            "category": m.category.value,
            "category_label": m.category.value.replace("_", " ").title(),
            "start": m.start,
            "end": m.end,
            "notes": m.notes,
        })
    return {
        "count": len(matches),
        "high": conf["high"],
        "medium": conf["medium"],
        "low": conf["low"],
        "ms": round(elapsed_ms, 2),
        "chars": len(text),
        "detectors": DETECTOR_COUNT,
        "highlighted": _highlight(text, matches),
        "matches": items,
    }


@app.post("/api/redact")
def api_redact(req: RedactReq):
    text = req.text or ""
    try:
        mode = RedactionMode(req.mode)
    except ValueError:
        return JSONResponse({"error": f"Unknown redaction mode: {req.mode}"}, status_code=400)
    try:
        result = scan_and_redact(text, mode, salt=_DEMO_SALT)
    except Exception:
        return JSONResponse({"error": "Something went wrong while redacting."}, status_code=400)
    return {"mode": mode.value, "original": text, "redacted": result.text, "count": result.count}
