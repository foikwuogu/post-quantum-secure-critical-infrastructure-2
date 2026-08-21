# Architecture: Hybrid PQC Migration for Simulated Payment Rails

## Hybrid key exchange protocol

```
Initiator                                          Responder
----------                                          ----------
                                                     has: X25519 keypair (A_priv, A_pub)
                                                          ML-KEM-768 keypair (K_pub, K_sec)

generate ephemeral X25519 keypair (E_priv, E_pub)
compute x25519_shared = ECDH(E_priv, A_pub)
encapsulate against K_pub:
   (ciphertext, mlkem_shared) = ML-KEM.Encaps(K_pub)

session_key = SHA256(x25519_shared || mlkem_shared)

send: E_pub, ciphertext  ────────────────────────▶
                                                     x25519_shared' = ECDH(A_priv, E_pub)
                                                     mlkem_shared' = ML-KEM.Decaps(K_sec, ciphertext)
                                                     session_key' = SHA256(x25519_shared' || mlkem_shared')

                                                     session_key' == session_key  ✓ (verified by /pqc/selftest)
```

Why combine with concatenation + SHA-256 rather than just using one or the
other: an adversary who wants to recover `session_key` must recover BOTH
`x25519_shared` (via breaking X25519 — a CRQC running Shor's algorithm) AND
`mlkem_shared` (via breaking ML-KEM — no known efficient quantum algorithm).
Production systems should use HKDF with proper domain separation instead of
raw SHA-256; this demo uses SHA-256 for readability.

## Dual-signing transition model

Real migrations don't cut over instantly — a payment message signed today
needs to validate against both upgraded and not-yet-upgraded receivers
during the transition window. `backend/app/pqc/signing.py` models this
directly:

```
sign(message) → { ecdsa_signature, mldsa_signature }   (both computed, both attached)

Not-yet-upgraded receiver: verify_classical_only(message, ecdsa_signature)  → validates as before
Upgraded receiver:         verify_pqc(message, mldsa_signature)             → validates with PQC guarantee
```

This is the practical shape of "crypto-agility" — the message carries both
signatures so verification behavior can be rolled out receiver-by-receiver
rather than requiring a synchronized flag-day cutover across every
participant on a payment rail.

## Why ML-KEM-768 and ML-DSA-65 specifically

- **ML-KEM-768** (not 512 or 1024): NIST's recommended default parameter
  set, targeting ~192-bit classical security — the same tier most
  organizations are standardizing on for near-term migration per current
  guidance (see the README's cited sources).
- **ML-DSA-65** (not 44 or 87): the mid-tier signature parameter set,
  comparable security tier to ML-KEM-768, balancing signature size (~3.3KB)
  against security margin.

🔲 If your paper specifies different parameter sets or a different hybrid
combiner (e.g. X-Wing instead of a raw concatenation+SHA-256), tell me and
I'll switch the implementation to match it exactly.

## The paper's governance/risk metrics (conceptual summary)

The published paper defines several metrics for prioritizing and auditing a
migration — summarized here conceptually rather than reproduced verbatim:

- **Quantum Risk Score** (Section 4.1.1): weighs how long a given asset's
  data must stay confidential and how long that asset will take to migrate,
  against the estimated time until a CRQC exists. Assets where the
  confidentiality/migration timeline exceeds the CRQC timeline are flagged
  as already exposed and prioritized first — e.g. long-lived mortgage
  records outrank a short-lived mobile session token.
- **Quantum Readiness Quotient** (Section 5.1.1): a weighted score across an
  institution's digital assets, where systemically important assets (core
  settlement ledgers) count more heavily than low-stakes ones (internal
  email), used by regulators to assess institutional preparedness against
  the NSM-10 2030/2035 targets.
- **Quantum Vulnerability Window** (Section 5.2.1): compares an
  institution's expected migration completion date against its data
  retention obligations and the expected CRQC arrival — a negative window
  means current data is already harvestable before migration finishes.

None of these are implemented as live-computed dashboard numbers yet, since
they depend on institution-specific inputs (actual data retention policies,
actual migration timelines) that this simulated environment doesn't have.
If you want these as real endpoints, tell me what per-asset/per-rail values
to use and I'll wire them in.

## Caveats (repeated from the README because they matter)

- The `pqcrypto` package calls in `hybrid_kex.py` and `signing.py` are
  written against its documented API (confirmed via public documentation/
  package listings), but were never executed in the sandbox that built this
  — no network access to `pip install`. Run `/pqc/selftest` first.
- `hndl_demo.py` is an educational explainer of the exposure model, not an
  actual quantum attack simulation — see the module docstring for why that
  distinction matters and is intentional.
