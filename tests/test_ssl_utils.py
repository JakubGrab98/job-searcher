import os

import certifi

from jobsearcher.ssl_utils import build_combined_ca_bundle


def test_combined_bundle_contains_standard_and_extra_certs(tmp_path):
    extra_cert_path = tmp_path / "extra.pem"
    extra_cert_path.write_text("-----BEGIN CERTIFICATE-----\nFAKE_EXTRA_CERT\n-----END CERTIFICATE-----\n")
    output_path = tmp_path / "combined.pem"

    result_path = build_combined_ca_bundle(str(extra_cert_path), str(output_path))

    assert result_path == str(output_path)
    combined_text = output_path.read_text()
    assert "FAKE_EXTRA_CERT" in combined_text

    with open(certifi.where(), encoding="utf-8") as f:
        standard_certs = f.read()
    assert standard_certs in combined_text


def test_combined_bundle_is_cached_when_extra_cert_unchanged(tmp_path):
    extra_cert_path = tmp_path / "extra.pem"
    extra_cert_path.write_text("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----\n")
    output_path = tmp_path / "combined.pem"

    build_combined_ca_bundle(str(extra_cert_path), str(output_path))
    first_mtime = os.path.getmtime(output_path)

    build_combined_ca_bundle(str(extra_cert_path), str(output_path))
    second_mtime = os.path.getmtime(output_path)

    assert first_mtime == second_mtime  # not rebuilt


def test_combined_bundle_rebuilds_when_extra_cert_changes(tmp_path):
    extra_cert_path = tmp_path / "extra.pem"
    output_path = tmp_path / "combined.pem"

    extra_cert_path.write_text("-----BEGIN CERTIFICATE-----\nOLD\n-----END CERTIFICATE-----\n")
    build_combined_ca_bundle(str(extra_cert_path), str(output_path))

    # Ensure the new mtime is distinguishable on filesystems with coarse
    # timestamp resolution.
    os.utime(extra_cert_path, (os.path.getmtime(extra_cert_path) + 5, os.path.getmtime(extra_cert_path) + 5))
    extra_cert_path.write_text("-----BEGIN CERTIFICATE-----\nNEW\n-----END CERTIFICATE-----\n")
    os.utime(extra_cert_path, (os.path.getmtime(output_path) + 5, os.path.getmtime(output_path) + 5))

    build_combined_ca_bundle(str(extra_cert_path), str(output_path))

    assert "NEW" in output_path.read_text()
