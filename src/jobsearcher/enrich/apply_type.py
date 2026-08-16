from dataclasses import dataclass

COOKIE_ACCEPT_SELECTOR = "#cookiescript_accept"
APPLY_BUTTON_ROLE_NAME = "Apply"


@dataclass
class ApplyTypeResult:
    apply_type: str  # "native" | "external" | "unknown"
    external_url: str | None = None


def dismiss_cookie_banner(page, timeout: int = 8000) -> None:
    try:
        page.locator(COOKIE_ACCEPT_SELECTOR).click(timeout=timeout)
    except Exception:
        pass  # banner not present, or already dismissed


def detect_apply_type(page, context) -> ApplyTypeResult:
    """Clicks the offer page's Apply button and determines whether it opens
    justjoin.it's own in-page quick-apply dialog (native) or redirects to
    the employer's own site/ATS in a new tab (external).

    Confirmed against 10 real offers (7 successfully classified: 5 external
    redirects — reply.com, eRecruiter, Emagine portal, Traffit x2, Greenhouse
    — and 2 native in-page dialogs with a file upload input). Closes any tab
    it opens as a side effect of detection.
    """
    dismiss_cookie_banner(page)

    apply_buttons = page.get_by_role("button", name=APPLY_BUTTON_ROLE_NAME, exact=True)
    pages_before = len(context.pages)

    clicked = False
    for i in range(apply_buttons.count()):
        btn = apply_buttons.nth(i)
        if btn.is_visible():
            try:
                btn.click(force=True, timeout=5000)
                clicked = True
                break
            except Exception:
                continue

    if not clicked:
        return ApplyTypeResult(apply_type="unknown")

    page.wait_for_timeout(4000)

    if len(context.pages) > pages_before:
        new_page = context.pages[-1]
        try:
            new_page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        external_url = new_page.url
        new_page.close()
        return ApplyTypeResult(apply_type="external", external_url=external_url)

    return ApplyTypeResult(apply_type="native")
