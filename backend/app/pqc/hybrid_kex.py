"""Hybrid post-quantum key exchange: ML-KEM-768 (FIPS 203) combined with
classical X25519 ECDH.

Hybrid construction rationale (matches current NIST/IETF guidance and the
approach your paper argues for): the session key is derived from BOTH
secrets, so an adversary must break BOTH primitives to recover it. If
ML-KEM turns out to have an unforeseen classical weakness, X25519 still
protects you. If a CRQC arrives and breaks X25519, ML-KEM still protects
you. This is why "hybrid," not "PQC-only," is the recommended near-term
migration posture.

⚠️ IMPLEMENTATION CAVEAT: this module is written against the documented API
of the `pqcrypto` package (pip install pqcrypto). I could not install or
execute this code in the sandbox that built it (no network access), so the
ML-KEM calls are syntax-checked but NOT verified end-to-end. Run
`GET /pqc/selftest` after `docker compose up` — if pqcrypto's actual API
differs from what's used below, paste the error and I'll fix it directly.
"""
import hashlib
import os

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

try:
    from pqcrypto.kem.ml_kem_768 import generate_keypair as _mlkem_generate_keypair
    from pqcrypto.kem.ml_kem_768 import encrypt as _mlkem_encapsulate
    from pqcrypto.kem.ml_kem_768 import decrypt as _mlkem_decapsulate
    PQCRYPTO_AVAILABLE = True
except ImportError:
    PQCRYPTO_AVAILABLE = False


class HybridKeyExchangeError(RuntimeError):
    pass


def generate_hybrid_keypair() -> dict:
    """Generates one X25519 keypair and one ML-KEM-768 keypair. In a real
    deployment these would be long-lived per-endpoint keys or ephemeral
    per-session keys, depending on your forward-secrecy requirements."""
    if not PQCRYPTO_AVAILABLE:
        raise HybridKeyExchangeError(
            "pqcrypto is not installed. `pip install pqcrypto` in the backend "
            "environment (see backend/requirements.txt)."
        )

    x25519_private = X25519PrivateKey.generate()
    x25519_public = x25519_private.public_key()

    mlkem_public, mlkem_secret = _mlkem_generate_keypair()

    return {
        "x25519_private": x25519_private,
        "x25519_public_bytes": x25519_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ),
        "mlkem_public_bytes": mlkem_public,
        "mlkem_secret_bytes": mlkem_secret,
    }


def initiator_encapsulate(responder_x25519_public_bytes: bytes, responder_mlkem_public_bytes: bytes) -> dict:
    """Initiator side: generates an ephemeral X25519 keypair, does ECDH
    against the responder's public key, AND encapsulates a shared secret
    against the responder's ML-KEM public key. Returns the combined session
    key plus everything the responder needs to derive the same key."""
    if not PQCRYPTO_AVAILABLE:
        raise HybridKeyExchangeError("pqcrypto is not installed.")

    ephemeral_private = X25519PrivateKey.generate()
    ephemeral_public_bytes = ephemeral_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    responder_public = X25519PublicKey.from_public_bytes(responder_x25519_public_bytes)
    x25519_shared = ephemeral_private.exchange(responder_public)

    mlkem_ciphertext, mlkem_shared = _mlkem_encapsulate(responder_mlkem_public_bytes)

    session_key = _combine_secrets(x25519_shared, mlkem_shared)

    return {
        "session_key": session_key,
        "ephemeral_x25519_public_bytes": ephemeral_public_bytes,
        "mlkem_ciphertext": mlkem_ciphertext,
    }


def responder_decapsulate(
    responder_x25519_private: X25519PrivateKey,
    responder_mlkem_secret_bytes: bytes,
    initiator_ephemeral_x25519_public_bytes: bytes,
    mlkem_ciphertext: bytes,
) -> bytes:
    """Responder side: derives the same session key from its own private
    keys plus what the initiator sent."""
    if not PQCRYPTO_AVAILABLE:
        raise HybridKeyExchangeError("pqcrypto is not installed.")

    initiator_public = X25519PublicKey.from_public_bytes(initiator_ephemeral_x25519_public_bytes)
    x25519_shared = responder_x25519_private.exchange(initiator_public)

    mlkem_shared = _mlkem_decapsulate(responder_mlkem_secret_bytes, mlkem_ciphertext)

    return _combine_secrets(x25519_shared, mlkem_shared)


def _combine_secrets(x25519_shared: bytes, mlkem_shared: bytes) -> bytes:
    """Combines both shared secrets into one session key. A production
    system should use a proper KDF (HKDF) with domain separation; SHA-256
    over the concatenation is used here for demo clarity."""
    return hashlib.sha256(x25519_shared + mlkem_shared).digest()


def selftest() -> dict:
    """Runs a full initiator/responder handshake locally and confirms both
    sides derive the same session key. This IS the thing to hit first after
    `docker compose up` to confirm pqcrypto's real API matches what's used
    above. Also reports the actual byte sizes involved, for the
    handshake-overhead comparison the paper discusses (ML-KEM-768 public
    keys/ciphertexts are far larger than X25519's 32 bytes)."""
    if not PQCRYPTO_AVAILABLE:
        return {"ok": False, "error": "pqcrypto not installed"}

    try:
        responder_keys = generate_hybrid_keypair()
        init_result = initiator_encapsulate(
            responder_keys["x25519_public_bytes"], responder_keys["mlkem_public_bytes"]
        )
        responder_session_key = responder_decapsulate(
            responder_keys["x25519_private"],
            responder_keys["mlkem_secret_bytes"],
            init_result["ephemeral_x25519_public_bytes"],
            init_result["mlkem_ciphertext"],
        )
        match = responder_session_key == init_result["session_key"]
        return {
            "ok": match,
            "session_keys_match": match,
            "session_key_hex_prefix": init_result["session_key"].hex()[:16],
            "sizes_bytes": {
                "x25519_public_key": len(responder_keys["x25519_public_bytes"]),
                "mlkem_public_key": len(responder_keys["mlkem_public_bytes"]),
                "mlkem_ciphertext": len(init_result["mlkem_ciphertext"]),
            },
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
