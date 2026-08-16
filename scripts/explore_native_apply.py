"""
One-off exploration: inspect the native quick-apply dialog's form fields and
selectors. Not part of the app's runtime pipeline.
"""

import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://justjoin.it/job-offer/emagine-polska-aml-kyc-analyst-warszawa-analytics"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)

        try:
            page.locator("#cookiescript_accept").click(timeout=8000)
            print("Dismissed cookie banner.")
        except Exception as e:
            print(f"Cookie banner dismiss failed/skip: {e}")

        apply_buttons = page.get_by_role("button", name="Apply", exact=True)
        for i in range(apply_buttons.count()):
            btn = apply_buttons.nth(i)
            if btn.is_visible():
                btn.click(force=True)
                break

        page.wait_for_timeout(1500)

        all_dialogs = page.locator("[role='dialog']")
        dialog_count = all_dialogs.count()
        print(f"=== {dialog_count} dialog(s) found ===")
        for i in range(dialog_count):
            d = all_dialogs.nth(i)
            try:
                snippet = d.inner_text(timeout=2000)[:80].replace("\n", " ")
            except Exception:
                snippet = "<unreadable>"
            print(f"  dialog[{i}]: {snippet!r}")

        # Pick the dialog that isn't the cookie banner.
        dialog = None
        for i in range(dialog_count):
            d = all_dialogs.nth(i)
            try:
                text = d.inner_text(timeout=2000)
            except Exception:
                continue
            if "cookies" not in text.lower():
                dialog = d
                break

        if dialog is None:
            print("\nNo non-cookie dialog found.")
            browser.close()
            return

        print("\n=== APPLY DIALOG TEXT ===")
        print(dialog.inner_text(timeout=3000))

        print("\n=== INPUT FIELDS IN DIALOG ===")
        inputs = dialog.locator("input, textarea, button[type='submit'], button")
        for i in range(inputs.count()):
            el = inputs.nth(i)
            tag = el.evaluate("e => e.tagName")
            itype = el.get_attribute("type")
            name = el.get_attribute("name")
            aria = el.get_attribute("aria-label")
            placeholder = el.get_attribute("placeholder")
            try:
                text = el.inner_text(timeout=500).strip()
            except Exception:
                text = ""
            print(f"  <{tag}> type={itype!r} name={name!r} aria-label={aria!r} placeholder={placeholder!r} text={text!r}")

        browser.close()


if __name__ == "__main__":
    main()
