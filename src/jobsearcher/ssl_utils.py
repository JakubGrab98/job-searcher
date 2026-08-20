import os

import certifi


def build_combined_ca_bundle(extra_cert_path: str, output_path: str = "secrets/combined_ca_bundle.pem") -> str:
    """Builds (and caches) a CA bundle containing both the standard public
    trust roots (certifi) and a custom intercepting cert (e.g. antivirus
    TLS inspection). Needed because whether a given connection actually
    gets intercepted varies by execution context — confirmed live: works
    fine interactively, fails under Windows Task Scheduler, because
    trusting ONLY the intercepting cert breaks the (apparently real)
    not-intercepted case, and trusting only the public roots breaks the
    intercepted case. Trusting both covers either outcome.
    """
    if os.path.exists(output_path) and os.path.getmtime(output_path) > os.path.getmtime(extra_cert_path):
        return output_path

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(certifi.where(), encoding="utf-8") as f:
        standard_certs = f.read()
    with open(extra_cert_path, encoding="utf-8") as f:
        extra_cert = f.read()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(standard_certs)
        f.write("\n")
        f.write(extra_cert)

    return output_path
