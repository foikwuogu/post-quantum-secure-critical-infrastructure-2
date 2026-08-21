import sys, os, json, tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "crypto_inventory"))
from scanner import scan_path, summarize  # noqa: E402


def _write(tmp: Path, name: str, content: str):
    p = tmp / name
    p.write_text(content)
    return p


def test_flags_rsa_python_usage(tmp_path):
    _write(tmp_path, "keys.py", "key = rsa.generate_private_key(public_exponent=65537, key_size=2048)\n")
    findings = scan_path(tmp_path)
    assert any(f.algorithm == "RSA" for f in findings)
    assert all(f.quantum_vulnerable for f in findings if f.algorithm == "RSA")


def test_flags_ecdsa_usage(tmp_path):
    _write(tmp_path, "sign.py", "sig = ECDSA(hashes.SHA256())\n")
    findings = scan_path(tmp_path)
    assert any(f.algorithm == "ECDSA/ECC" for f in findings)


def test_flags_openssl_cli_rsa(tmp_path):
    _write(tmp_path, "gen.sh", "#!/bin/bash\nopenssl genrsa -out ca.key 4096\n")
    findings = scan_path(tmp_path)
    assert any(f.algorithm == "RSA (openssl CLI)" for f in findings)


def test_pqc_usage_flagged_as_not_vulnerable(tmp_path):
    _write(tmp_path, "kem.py", "pk, sk = ml_kem_768.generate_keypair()\n")
    findings = scan_path(tmp_path)
    ml_kem_findings = [f for f in findings if f.algorithm == "ML-KEM/Kyber"]
    assert len(ml_kem_findings) == 1
    assert ml_kem_findings[0].quantum_vulnerable is False


def test_clean_file_has_no_findings(tmp_path):
    _write(tmp_path, "app.py", "def add(a, b):\n    return a + b\n")
    findings = scan_path(tmp_path)
    assert findings == []


def test_summary_counts_match_findings(tmp_path):
    _write(tmp_path, "mixed.py", "rsa.generate_private_key()\nECDSA(hashes.SHA256())\n")
    findings = scan_path(tmp_path)
    summary = summarize(findings)
    assert summary["total_findings"] == len(findings)
    assert summary["quantum_vulnerable_findings"] == sum(1 for f in findings if f.quantum_vulnerable)
