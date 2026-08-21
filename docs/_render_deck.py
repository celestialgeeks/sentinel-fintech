"""Render SENTINEL_DECK.html to a print-quality PDF using Playwright Chromium.

We use Chrome's print-to-PDF rather than WeasyPrint because:
- WeasyPrint needs native pango libs (not installed on this macOS env)
- Chrome handles web fonts + dark theme + page-size CSS correctly
- print_background=True keeps the dark canvas and indigo accents
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = Path("/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/SENTINEL_DECK.html").resolve()
OUT  = Path("/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/SENTINEL_DECK.pdf").resolve()

assert HTML.exists(), f"HTML not found: {HTML}"
OUT.parent.mkdir(parents=True, exist_ok=True)

# 16:9 landscape, 1920x1080 CSS px. Chrome pdf uses inches/px; pass width/height in inches.
# 1920px / 96dpi = 20in, 1080 / 96 = 11.25in. But @page is 13.33in x 7.5in (= 1920x1080 at 144dpi).
# Use 13.33in x 7.5in to match the @page declaration.
WIDTH_IN  = 13.3333
HEIGHT_IN = 7.5

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page = ctx.new_page()
    page.goto(HTML.as_uri(), wait_until="networkidle", timeout=60000)
    # Wait for web fonts so the printed PDF has real Inter (not fallback).
    try:
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(800)
    except Exception:
        pass

    # Hard-set viewport to the PDF page size to avoid any layout shift in print
    pdf_bytes = page.pdf(
        path=str(OUT),
        width=f"{WIDTH_IN}in",
        height=f"{HEIGHT_IN}in",
        print_background=True,
        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        prefer_css_page_size=True,
    )
    browser.close()

print(f"OK  {OUT}  ({OUT.stat().st_size:,} bytes)")
