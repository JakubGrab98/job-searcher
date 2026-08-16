"""
One-off validation: render the real cv_library.yaml (full default selection)
to a PDF so the output can be visually checked against the reference CV
design. Not part of the app's runtime pipeline.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jobsearcher.tailor.cv_library import load_cv_library  # noqa: E402
from jobsearcher.tailor.cv_render import render_cv_html, render_cv_pdf  # noqa: E402
from jobsearcher.tailor.selection import default_selection  # noqa: E402


def main():
    library = load_cv_library("config/cv_library.yaml")
    selection = default_selection(library)
    html = render_cv_html(library, selection)

    output_path = "scripts/_cv_preview.pdf"
    render_cv_pdf(html, output_path)
    print(f"Rendered PDF to {output_path}")

    with open("scripts/_cv_preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Also wrote scripts/_cv_preview.html for quick inspection")


if __name__ == "__main__":
    main()
