# Post-Quantum Secure Critical Infrastructure

A research prototype demonstrating **hybrid post-quantum cryptography (PQC)
migration** for critical financial payment infrastructure, built as the
practical implementation layer for:

> Ikwuogu, O. F., Agbesi, J. S., Eni, F., Titilayo, D. H., & Zeyeum, J. N.
> *Quantum-Resilient Infrastructure: Migrating US Financial
> Payment System to Post-Quantum Cryptography (PQC) Standards to Prevent
> 'Harvest Now, Decrypt Later' Attacks.*

> **Status:** research/lab prototype. All payment rails (FedWire-style
> real-time gross settlement, CHIPS-style net settlement, ACH-style batch
> processing) are **simulated services**. Nothing here connects to a real
> payment network, and it should never be pointed at one.

> **Note on scope:** built and aligned against the full published paper
> (IJCATR Vol. 13, Issue 12, 2024, DOI:10.7753/IJCATR1312.1016). Figures for
> key/signature sizes, the classical-vs-hybrid architecture, and the
> dual-signature/composite-verification model below are drawn directly from
> it. The paper's Quantum Risk Score, Quantum Readiness Quotient, and
> Quantum Vulnerability Window metrics (Sections 4.1.1, 5.1.1, 5.2.1) are
> summarized conceptually in `docs/architecture.md` rather than reproduced
> verbatim — implement the exact weightings you used in your analysis if you
> want the dashboard to report your specific numbers rather than the
> illustrative ones here.

---

## 1. Problem

Current US payment rails — FedWire, CHIPS, and ACH — depend on RSA and ECC
for key exchange and digital signatures. Both are broken by Shor's algorithm
on a cryptographically relevant quantum computer (CRQC). Because encrypted
traffic and signed records are often retained for years (settlement records,
audit trails, archived messages), a CRQC does not need to exist *today* to
create risk today: adversaries can harvest ciphertext now and decrypt it
once a CRQC exists — the "Harvest Now, Decrypt Later" (HNDL) threat.

## 2. Research question

> Can a hybrid classical+post-quantum cryptographic architecture (ML-KEM for
> key encapsulation, ML-DSA for signatures) be integrated into simulated
> US payment-rail message flows without breaking interoperability, while
> measurably closing the HNDL exposure window that pure RSA/ECC leaves open?

## 3. Architecture

```
                        ┌─────────────────────────────┐
  Originating bank  ───▶│   Payment Gateway (FastAPI)  │───▶  Simulated rail
  (simulated)           │   - Hybrid KEM handshake     │      (FedWire / CHIPS
                         │     (X25519 + ML-KEM-768)    │       / ACH stand-in)
                         │   - Message signing          │
                         │     (ECDSA + ML-DSA-65,       │
                         │      dual-signed during        │
                         │      migration)                │
                         │   - Crypto-agility layer      │
                         │     (algorithm selectable     │
                         │      per message/session)     │
                         └──────────────┬───────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          ▼                            ▼
                 Classical-only path           Hybrid PQC path
                 (RSA/ECDSA — HNDL-exposed)     (ML-KEM/ML-DSA — HNDL-resistant)
```

Every simulated payment message can be routed down either path so the demo
can show, side by side, what an adversary harvesting today's traffic can and
cannot eventually do to each.

## 4. Methodology

- **Simulated rails:** lightweight stand-ins for a FedWire-style RTGS
  message, a CHIPS-style net-settlement batch, and an ACH-style batch file —
  enough structure (originator, beneficiary, amount, settlement date,
  reference) to carry real cryptographic operations without touching a real
  network.
- **Hybrid key exchange:** ML-KEM-768 (FIPS 203) combined with classical
  X25519 ECDH, per NIST/IETF hybrid-KEM guidance — if either primitive holds,
  the session key holds.
- **Signatures:** ML-DSA-65 (FIPS 204) alongside classical ECDSA, with a
  configurable **dual-signing** mode that mirrors how real migrations
  actually run (classical signature kept for backward compatibility during
  transition, PQC signature added alongside it) — see `docs/architecture.md`.
- **Cryptographic dependency inventory:** a standalone scanner
  (`crypto_inventory/`) that walks a codebase and flags classical
  public-key crypto usage (RSA, ECDSA, ECDH, DH, plain X.509 without a PQC
  hybrid), producing a CBOM-style (Cryptographic Bill of Materials) JSON
  report — the practical tool version of your paper's "cryptographic
  dependency inventory" step.
- **HNDL exposure demonstration:** `backend/app/services/hndl_demo.py`
  encrypts the same simulated payment message down both paths and produces
  an explicit, side-by-side explanation of what a ciphertext-harvesting
  adversary holds in each case (see the caveat in that module — this is an
  educational illustration, not an actual cryptanalytic attack).
- **Evaluation metrics:** handshake/signing latency overhead of hybrid vs.
  classical-only (measured, not estimated), inventory scanner precision on a
  seeded test corpus, and qualitative HNDL-exposure-window comparison.

## 5. Experiments

| Scenario                                   | Classical-only (RSA/ECDSA) | Hybrid PQC (ML-KEM/ML-DSA) |
|---------------------------------------------|------------------------------|-------------------------------|
| Ciphertext harvested today, CRQC arrives    | Confidentiality broken retroactively | Confidentiality preserved (ML-KEM security doesn't reduce to factoring/DLOG) |
| Signature forgery post-CRQC                 | Forgeable                    | Not forgeable via Shor's algorithm |
| Public key size (X25519 vs ML-KEM-768)      | 32 bytes                     | 1,184 bytes                   |
| Handshake ciphertext size                   | n/a                           | 1,088 bytes                   |
| Signature size (ECDSA vs ML-DSA-65)         | ~64 bytes                    | ~3,293 bytes (~50x)           |
| MTU fragmentation risk (1,500-byte Ethernet)| single packet                | typically 3+ fragments — the paper's case for Jumbo Frames on Fed backbones |
| Handshake latency                           | baseline                     | measured overhead (see `/pqc/selftest` and the Grafana dashboard) |
| Crypto-agility (swap algorithm without re-architecture) | No             | Yes — algorithm selected per session |
| Dependency visibility                        | Manual                       | Automated (CBOM scanner)      |

The size figures above are the paper's own published numbers for ML-KEM-768
and ML-DSA-65 vs. their classical equivalents. The dashboard reports the
*actual* measured sizes from the running `pqcrypto` calls, so you can
directly confirm the demo matches the paper's published figures.

## Repository layout

```
backend/app/pqc/            hybrid_kex.py (ML-KEM-768 + X25519), signing.py (ML-DSA-65 + ECDSA)
backend/app/simulated_rails/ FedWire / CHIPS / ACH message stand-ins
backend/app/services/        payment_gateway.py, hndl_demo.py, benchmark.py
backend/app/routers/         FastAPI endpoints
crypto_inventory/            standalone CBOM scanner (works on ANY codebase, not just this one)
docs/architecture.md         full protocol detail + honest caveats on the PQC libraries used
tests/                       scanner tests (verified) + crypto module tests (see caveats)
```

## Quickstart

```bash
docker compose up --build
# API: http://localhost:8100/docs
```

Run the crypto inventory scanner against any codebase (including this one):

```bash
python3 crypto_inventory/scanner.py --path /path/to/scan --out cbom-report.json
```

## Tech stack

FastAPI (Python) · `pqcrypto` (ML-KEM-768 / ML-DSA-65 reference bindings) ·
`cryptography` (classical X25519/ECDSA baseline) · Docker Compose

## Roadmap

- ✅ Backend API (`/payments/process`, `/payments/compare`, `/pqc/selftest`),
  hybrid KEM + dual-signing modules, simulated FedWire/CHIPS/ACH messages,
  HNDL exposure explainer — all implemented.
- ✅ Crypto inventory / CBOM scanner — tested and verified working, including
  against project 1's own repo (correctly flagged its RSA cert generation).
- ✅ React comparison dashboard (`frontend/`) — submits a simulated payment,
  runs it down both paths, and shows handshake/signing latency plus a
  wire-size overhead visualization using the paper's own published figures.
- ✅ Grafana dashboard (auto-provisioned, `grafana/dashboards/pqc-overview.json`)
  — payments-by-path, payments-by-rail, and handshake/signing latency
  percentiles (classical vs. hybrid), sourced live from `/metrics`.
- 🔲 The paper's Quantum Risk Score / Quantum Readiness Quotient / Quantum
  Vulnerability Window metrics are described conceptually in
  `docs/architecture.md` but not wired into the dashboard as live-computed
  numbers — tell me if you want those implemented with your specific
  weightings from the paper.

## Honest status of what's real vs. what needs your verification

- ✅ Crypto inventory / CBOM scanner — pure Python, no external crypto deps,
  **I ran it in this sandbox and it works** (see `tests/`).
- ✅ Simulated payment message structures (FedWire/CHIPS/ACH stand-ins) and
  the payment gateway wiring — plain Python, tested.
- 🚧 The actual ML-KEM/ML-DSA calls in `backend/app/pqc/` are written against
  the `pqcrypto` package's documented API, but **I could not `pip install`
  or execute them in this sandbox (no network access here)**. Syntax is
  checked; the actual cryptographic calls are not yet verified end-to-end.
  Run `docker compose up --build` and check `/pqc/selftest` first — if the
  API doesn't match your installed version, tell me the error and I'll fix
  it directly.
- 🔲 Your paper's specific governance framework, experimental results, and
  any named algorithm parameter choices beyond ML-KEM/ML-DSA — paste the
  relevant sections and I'll align the README and code precisely.

## Citation

Ikwuogu, O. F., Agbesi, J. S., Eni, F., Titilayo, D. H., & Zeyeum, J. N.
*Quantum-Resilient Infrastructure: Migrating US Financial Payment System to
Post-Quantum Cryptography (PQC) Standards to Prevent 'Harvest Now, Decrypt
Later' Attacks.* International Journal of Computer Applications Technology
and Research, 13(12), 198–213, 2024. DOI: 10.7753/IJCATR1312.1016.
