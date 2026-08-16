"""
One-off exploration: dump the rendered offer page's visible text and probe
likely selectors for description/tech-stack/salary/seniority/employment-type/
location fields. Not part of the app's runtime pipeline.
"""

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://justjoin.it/job-offer/reply-polska-sp-z-o-o--senior-business-analyst-katowice-analytics-229f90b9"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)

        try:
            page.locator("#cookiescript_accept").click(timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(500)

        body_text = page.locator("body").inner_text(timeout=5000)
        with open("scripts/_offer_page_text.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
        print(f"Visible body text ({len(body_text)} chars) written to scripts/_offer_page_text.txt")

        # Common data-testid / class patterns to probe.
        print("\n=== Probing likely selectors ===")
        probes = [
            "[data-testid]",
            "[class*='skill']",
            "[class*='Skill']",
            "[class*='tag']",
            "[class*='Tag']",
            "[class*='salary']",
            "[class*='Salary']",
        ]
        for sel in probes:
            count = page.locator(sel).count()
            print(f"{sel}: {count} matches")

        testids = page.eval_on_selector_all(
            "[data-testid]", "els => [...new Set(els.map(e => e.getAttribute('data-testid')))]"
        )
        print(f"\nUnique data-testid values ({len(testids)}):")
        for t in sorted(testids):
            print(f"  {t}")

        browser.close()


if __name__ == "__main__":
    main()
