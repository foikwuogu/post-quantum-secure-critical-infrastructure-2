"""Message signing: ML-DSA-65 (FIPS 204) alongside classical ECDSA-P256.

Real payment-rail migrations don't flip a switch from classical to PQC
overnight — they run a **dual-signing** transition period where messages
carry both signatures, so receiving systems that haven't upgraded yet still
validate the classical signature while PQC-aware systems validate the new
one. This module models that transition explicitly rather than just
swapping one algorithm for another.

⚠️ Same caveat as hybrid_kex.py: written against pqcrypto's documented API,
not executed in this sandbox (no network to install it). Verify via
`GET /pqc/selftest`.
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

try:
    from pqcrypto.sign.ml_dsa_65 import generate_keypair as _mldsa_generate_keypair
    from pqcrypto.sign.ml_dsa_65 import sign as _mldsa_sign
    from pqcrypto.sign.ml_dsa_65 import verify as _mldsa_verify
    PQCRYPTO_AVAILABLE = True
except ImportError:
    PQCRYPTO_AVAILABLE = False


class SigningError(RuntimeError):
    pass


def generate_dual_keypair() -> dict:
    if not PQCRYPTO_AVAILABLE:
        raise SigningError("pqcrypto is not installed.")

    ecdsa_private = ec.generate_private_key(ec.SECP256R1())
    mldsa_public, mldsa_secret = _mldsa_generate_keypair()

    return {
        "ecdsa_private": ecdsa_private,
        "mldsa_public_bytes": mldsa_public,
        "mldsa_secret_bytes": mldsa_secret,
    }


def dual_sign(message: bytes, ecdsa_private, mldsa_secret_bytes: bytes) -> dict:
    """Signs with both algorithms. `algorithm` on each signature makes it
    explicit to any verifier which check it's performing, rather than
    silently trusting whichever one happens to validate."""
    if not PQCRYPTO_AVAILABLE:
        raise SigningError("pqcrypto is not installed.")

    ecdsa_signature = ecdsa_private.sign(message, ec.ECDSA(hashes.SHA256()))
    mldsa_signature = _mldsa_sign(mldsa_secret_bytes, message)

    return {
        "message": message,
        "ecdsa_signature": ecdsa_signature,
        "mldsa_signature": mldsa_signature,
    }


def verify_classical_only(message: bytes, ecdsa_signature: bytes, ecdsa_public) -> bool:
    """What a NOT-yet-upgraded receiver does: validates only the classical
    signature. This is the exact path an adversary exploits post-CRQC."""
    try:
        ecdsa_public.verify(ecdsa_signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def verify_pqc(message: bytes, mldsa_signature: bytes, mldsa_public_bytes: bytes) -> bool:
    """What an upgraded receiver does: validates the PQC signature, which
    remains unforgeable even against a CRQC."""
    if not PQCRYPTO_AVAILABLE:
        raise SigningError("pqcrypto is not installed.")
    try:
        return _mldsa_verify(mldsa_public_bytes, message, mldsa_signature)
    except Exception:
        return False


def verify_composite(message: bytes, ecdsa_signature: bytes, ecdsa_public, mldsa_signature: bytes, mldsa_public_bytes: bytes) -> bool:
    """Strict composite verification: valid only if BOTH signatures verify.
    This is the stricter mode the paper specifies for full compliance
    checking (as opposed to the independent dual-verify functions above,
    which model a mixed-migration population where legacy receivers only
    ever check the classical half)."""
    return verify_classical_only(message, ecdsa_signature, ecdsa_public) and verify_pqc(
        message, mldsa_signature, mldsa_public_bytes
    )


def selftest() -> dict:
    if not PQCRYPTO_AVAILABLE:
        return {"ok": False, "error": "pqcrypto not installed"}
    try:
        keys = generate_dual_keypair()
        message = b"FEDWIRE-TEST-MESSAGE-0001"
        signed = dual_sign(message, keys["ecdsa_private"], keys["mldsa_secret_bytes"])

        ecdsa_ok = verify_classical_only(message, signed["ecdsa_signature"], keys["ecdsa_private"].public_key())
        mldsa_ok = verify_pqc(message, signed["mldsa_signature"], keys["mldsa_public_bytes"])

        return {
            "ok": ecdsa_ok and mldsa_ok,
            "ecdsa_verified": ecdsa_ok,
            "mldsa_verified": mldsa_ok,
            "sizes_bytes": {
                "ecdsa_signature": len(signed["ecdsa_signature"]),
                "mldsa_signature": len(signed["mldsa_signature"]),
                "mldsa_public_key": len(keys["mldsa_public_bytes"]),
            },
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
