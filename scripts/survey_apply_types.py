"""
One-off survey: run jobsearcher.enrich.apply_type.detect_apply_type against
real offer URLs to validate it against known-manual classifications.
Not part of the app's runtime pipeline.

Run: .venv/Scripts/python.exe scripts/survey_apply_types.py
"""

import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.enrich.apply_type import detect_apply_type  # noqa: E402

URLS = [
    "https://justjoin.it/job-offer/reply-polska-sp-z-o-o--senior-business-analyst-katowice-analytics-229f90b9",
    "https://justjoin.it/job-offer/jit-team-business-analyst-scoring-engineer-lodz-analytics",
    "https://justjoin.it/job-offer/itlt-business-analyst-monitoring-systems--warszawa-analytics",
    "https://justjoin.it/job-offer/bluesoft-ai-analyst-warszawa-analytics",
    "https://justjoin.it/job-offer/emagine-polska-front-office-business-analyst-london-analytics",
    "https://justjoin.it/job-offer/emagine-polska-junior-business-analyst-lisbon-analytics",
    "https://justjoin.it/job-offer/emagine-polska-requirements-engineer-warsaw-analytics",
    "https://justjoin.it/job-offer/capco-poland-business-analyst---accounting-krakow-analytics",
    "https://justjoin.it/job-offer/emagine-polska-aml-kyc-analyst-warszawa-analytics",
    "https://justjoin.it/job-offer/hcltech-senior-it-analyst-with-bulgarian-english-krakow-analytics",
]

EXPECTED = {
    "reply-polska-sp-z-o-o--senior-business-analyst-katowice-analytics-229f90b9": "external",
    "jit-team-business-analyst-scoring-engineer-lodz-analytics": "external",
    "itlt-business-analyst-monitoring-systems--warszawa-analytics": "external",
    "bluesoft-ai-analyst-warszawa-analytics": "external",
    "emagine-polska-front-office-business-analyst-london-analytics": "external",
    "emagine-polska-junior-business-analyst-lisbon-analytics": "external",
    "emagine-polska-requirements-engineer-warsaw-analytics": "external",
    "capco-poland-business-analyst---accounting-krakow-analytics": "external",
    "emagine-polska-aml-kyc-analyst-warszawa-analytics": "native",
    "hcltech-senior-it-analyst-with-bulgarian-english-krakow-analytics": "native",
}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        mismatches = 0

        for url in URLS:
            slug = url.rstrip("/").split("/")[-1]
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)  # let the SPA hydrate
                result = detect_apply_type(page, context)
            except Exception as e:
                result = None
                print(f"{slug}\n  -> ERROR: {e}\n")
            finally:
                page.close()

            if result is not None:
                expected = EXPECTED.get(slug)
                match = "OK" if result.apply_type == expected else "MISMATCH"
                if match == "MISMATCH":
                    mismatches += 1
                print(f"{slug}\n  -> {result.apply_type} (expected {expected}) [{match}]")
                if result.external_url:
                    print(f"     external_url={result.external_url}")
                print()

        browser.close()
        print(f"Done. {mismatches} mismatch(es) out of {len(URLS)}.")


if __name__ == "__main__":
    main()
