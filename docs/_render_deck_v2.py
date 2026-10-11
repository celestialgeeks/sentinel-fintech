"""Render SENTINEL_DECK_V2.html to PDF using Playwright Chromium.
Stripe design system — white canvas, deep navy, signature purple.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = Path("/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/SENTINEL_DECK_V2.html").resolve()
OUT  = Path("/Users/shreyashsingh/my info/projects/sentinel-fintech/docs/SENTINEL_DECK_V2.pdf").resolve()

assert HTML.exists(), f"HTML not found: {HTML}"
OUT.parent.mkdir(parents=True, exist_ok=True)

WIDTH_IN  = 13.3333
HEIGHT_IN = 7.5

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page = ctx.new_page()
    page.goto(HTML.as_uri(), wait_until="networkidle", timeout=60000)
    try:
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(1000)
    except Exception:
        pass

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
