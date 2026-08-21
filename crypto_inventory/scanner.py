#!/usr/bin/env python3
"""Cryptographic dependency inventory scanner (CBOM-style).

Walks a codebase and flags usage of classical public-key cryptography that
is vulnerable to Shor's algorithm (RSA, ECDSA, ECDH/DH, plain X.509 without
a PQC hybrid) — the practical tool version of the "cryptographic dependency
inventory" step every PQC migration framework calls for.

This is intentionally a standalone script with zero third-party
dependencies, so it can be pointed at ANY codebase (not just this repo)
without needing that codebase's environment set up.

Usage:
    python3 scanner.py --path /path/to/scan --out cbom-report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

# Pattern -> (algorithm, quantum_vulnerable, note)
PATTERNS = [
    (re.compile(r"\bRSA\.generate\b|\brsa\.generate_private_key\b|\bRSA\.import_key\b"), "RSA", True, "Key generation/import - broken by Shor's algorithm"),
    (re.compile(r"\bRSAES?-?PKCS1\b|\bPKCS1_OAEP\b|\bPKCS1_v1_5\b"), "RSA-PKCS1", True, "RSA encryption padding scheme"),
    (re.compile(r"\bECDSA\b|\bec\.generate_private_key\b|\bSECP256R1\b|\bSECP384R1\b|\bsecp256k1\b"), "ECDSA/ECC", True, "Elliptic-curve signatures - broken by Shor's algorithm"),
    (re.compile(r"\bECDH\b|\bX25519\b|\bX448\b"), "ECDH", True, "Elliptic-curve key exchange - broken by Shor's algorithm (fine as the classical half of a HYBRID exchange, flagged here for inventory visibility)"),
    (re.compile(r"\bDiffieHellman\b|\bDH\.generate_parameters\b"), "DH", True, "Finite-field Diffie-Hellman - broken by Shor's algorithm"),
    (re.compile(r"\bopenssl\s+genrsa\b|\bopenssl\s+req\b.*-newkey\s+rsa"), "RSA (openssl CLI)", True, "RSA key generated via openssl CLI - broken by Shor's algorithm"),
    (re.compile(r"\bopenssl\s+ecparam\b|-newkey\s+ec\b"), "ECDSA (openssl CLI)", True, "EC key generated via openssl CLI - broken by Shor's algorithm"),
    (re.compile(r"\bssl\.PROTOCOL_TLSv1(?!\.3)\b|\bssl\.PROTOCOL_SSLv"), "Legacy TLS/SSL", True, "Deprecated protocol version - also typically classical-only key exchange"),
    (re.compile(r"\bMD5\b|\bSHA1\b(?!\d)"), "MD5/SHA1", False, "Weak classical hash - not quantum-specific, but worth inventorying alongside crypto-agility work"),
    (re.compile(r"\bml_kem\w*|\bML-KEM\b|\bkyber\b|\bKyber\b"), "ML-KEM/Kyber", False, "Post-quantum KEM already in use - good"),
    (re.compile(r"\bml_dsa\w*|\bML-DSA\b|\bdilithium\b|\bDilithium\b"), "ML-DSA/Dilithium", False, "Post-quantum signature already in use - good"),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".pytest_cache"}
SCAN_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".c", ".cpp", ".cs", ".rb", ".yml", ".yaml", ".conf", ".cnf", ".sh"}
SCAN_FILENAMES = {"Dockerfile"}


@dataclass
class Finding:
    file: str
    line: int
    algorithm: str
    quantum_vulnerable: bool
    note: str
    snippet: str


def scan_file(path: Path) -> List[Finding]:
    findings = []
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, algorithm, vulnerable, note in PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        file=str(path),
                        line=lineno,
                        algorithm=algorithm,
                        quantum_vulnerable=vulnerable,
                        note=note,
                        snippet=line.strip()[:160],
                    )
                )
    return findings


def scan_path(root: Path) -> List[Finding]:
    all_findings: List[Finding] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in SCAN_EXTENSIONS and path.name not in SCAN_FILENAMES:
            continue
        all_findings.extend(scan_file(path))
    return all_findings


def summarize(findings: List[Finding]) -> dict:
    by_algorithm = {}
    for f in findings:
        by_algorithm.setdefault(f.algorithm, {"count": 0, "quantum_vulnerable": f.quantum_vulnerable})
        by_algorithm[f.algorithm]["count"] += 1

    vulnerable_count = sum(1 for f in findings if f.quantum_vulnerable)
    return {
        "total_findings": len(findings),
        "quantum_vulnerable_findings": vulnerable_count,
        "by_algorithm": by_algorithm,
    }


def main():
    parser = argparse.ArgumentParser(description="Cryptographic dependency inventory scanner")
    parser.add_argument("--path", required=True, help="Directory to scan")
    parser.add_argument("--out", default="cbom-report.json", help="Output JSON report path")
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    findings = scan_path(root)
    report = {
        "scanned_path": str(root.resolve()),
        "summary": summarize(findings),
        "findings": [asdict(f) for f in findings],
    }

    Path(args.out).write_text(json.dumps(report, indent=2))
    print(f"Scanned {report['summary']['total_findings']} findings "
          f"({report['summary']['quantum_vulnerable_findings']} quantum-vulnerable) "
          f"across {root}. Report written to {args.out}")


if __name__ == "__main__":
    main()
