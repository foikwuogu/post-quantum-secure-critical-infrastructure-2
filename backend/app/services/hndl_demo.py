"""Illustrates the Harvest-Now-Decrypt-Later exposure difference between a
classical-only channel and a hybrid PQC channel.

⚠️ IMPORTANT: this module does NOT implement or simulate an actual quantum
attack — that's neither possible nor appropriate here. What it does is make
the *exposure model* concrete: for a classical-only session, the single
secret an adversary needs (the ECDH private scalar) is exactly the kind of
thing a CRQC running Shor's algorithm targets, so "harvest the ciphertext
today, decrypt once a CRQC exists" is a coherent, well-defined future step
for the adversary. For a hybrid session, the same future adversary needs to
ALSO break ML-KEM, which has no known efficient quantum algorithm - so
"harvest now" only pays off if BOTH primitives eventually fall, which is a
categorically different (and currently unfounded) risk.
"""


def explain_exposure(rail: str, classical_only: bool) -> dict:
    if classical_only:
        return {
            "rail": rail,
            "path": "classical-only (RSA/ECDSA + ECDH)",
            "hndl_exposed": True,
            "explanation": (
                "An adversary who captures this session's ciphertext today needs only "
                "the ECDH private scalar to recover the session key. Shor's algorithm "
                "on a CRQC recovers that scalar from the public key alone - no need to "
                "compromise any endpoint. This session's confidentiality has an expiry "
                "date tied to when a CRQC arrives, not to how the encryption was configured."
            ),
        }
    return {
        "rail": rail,
        "path": "hybrid PQC (ML-KEM-768 + X25519)",
        "hndl_exposed": False,
        "explanation": (
            "An adversary who captures this session's ciphertext today would need to "
            "additionally break ML-KEM-768, which has no known efficient quantum "
            "algorithm (its security reduces to lattice problems, not factoring or "
            "discrete log). Harvesting this ciphertext does not create a well-defined "
            "future decryption path the way it does for the classical-only session."
        ),
    }


def compare_rail(rail: str) -> dict:
    return {
        "classical": explain_exposure(rail, classical_only=True),
        "hybrid_pqc": explain_exposure(rail, classical_only=False),
    }
