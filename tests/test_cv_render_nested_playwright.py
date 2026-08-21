"""
Regression test for a real production bug: render_cv_pdf() used to open its
own sync_playwright() context unconditionally, which collides when a caller
(run.py) already has one open for enrichment — Playwright's sync API does
not support nested contexts in the same process ("you are using Playwright
Sync API inside the asyncio loop"). This only manifested in the real
pipeline (enrichment's browser stays open across the whole run, tailoring
happens inside that same run) — every earlier validation script ran
enrichment and tailoring as separate, sequential sync_playwright() blocks,
never nested, so this slipped through until a live run hit it for real.

Uses a real Playwright browser (not mocked) specifically to catch this
class of bug — a fake render function, like the one used in test_tailor.py,
cannot detect a real Playwright API misuse.
"""

import os

from playwright.sync_api import sync_playwright

from jobsearcher.tailor.cv_render import render_cv_pdf

MINIMAL_HTML = "<html><body><h1>Test CV</h1></body></html>"


def test_render_cv_pdf_works_while_an_outer_playwright_context_is_open(tmp_path):
    # Simulates run.py's real shape: an outer sync_playwright() is already
    # open (for enrichment) when render_cv_pdf() gets called for tailoring.
    output_path = str(tmp_path / "cv.pdf")

    with sync_playwright() as outer_p:
        outer_browser = outer_p.chromium.launch()
        outer_page = outer_browser.new_page()  # the enrichment browser being in use

        render_cv_pdf(MINIMAL_HTML, output_path, browser=outer_browser)

        outer_page.close()
        outer_browser.close()

    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0


def test_render_cv_pdf_still_works_standalone_without_a_shared_browser(tmp_path):
    # The non-run.py case (e.g. validate_cv_render.py) — no browser passed,
    # falls back to managing its own Playwright context.
    output_path = str(tmp_path / "cv_standalone.pdf")

    render_cv_pdf(MINIMAL_HTML, output_path)

    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0
