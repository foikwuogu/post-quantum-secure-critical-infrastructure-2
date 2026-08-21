import time

from ..simulated_rails.messages import BUILDERS
from ..pqc import hybrid_kex, signing
from .hndl_demo import compare_rail
from . import metrics


def process_payment(rail: str, originator: str, beneficiary: str, amount_usd: float, reference: str, path: str) -> dict:
    """path: 'classical' or 'hybrid_pqc'. Builds the message, runs the
    corresponding handshake/signing, and reports timing + HNDL exposure."""
    if rail not in BUILDERS:
        raise ValueError(f"unknown rail '{rail}', expected one of {list(BUILDERS)}")
    if path not in ("classical", "hybrid_pqc"):
        raise ValueError("path must be 'classical' or 'hybrid_pqc'")

    message = BUILDERS[rail](originator, beneficiary, amount_usd, reference)
    payload = message.to_bytes()

    result = {"message": message.__dict__, "path": path}

    if path == "hybrid_pqc":
        t0 = time.perf_counter()
        selftest = hybrid_kex.selftest()
        kex_ms = (time.perf_counter() - t0) * 1000
        result["handshake"] = {**selftest, "elapsed_ms": round(kex_ms, 3)}

        t0 = time.perf_counter()
        sign_selftest = signing.selftest()
        sign_ms = (time.perf_counter() - t0) * 1000
        result["signing"] = {**sign_selftest, "elapsed_ms": round(sign_ms, 3)}
    else:
        # Classical-only path: plain X25519 ECDH + ECDSA, no PQC component.
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes

        t0 = time.perf_counter()
        a = X25519PrivateKey.generate()
        b = X25519PrivateKey.generate()
        shared_a = a.exchange(b.public_key())
        shared_b = b.exchange(a.public_key())
        kex_ms = (time.perf_counter() - t0) * 1000
        result["handshake"] = {"ok": shared_a == shared_b, "elapsed_ms": round(kex_ms, 3)}

        t0 = time.perf_counter()
        priv = ec.generate_private_key(ec.SECP256R1())
        sig = priv.sign(payload, ec.ECDSA(hashes.SHA256()))
        verified = True
        try:
            priv.public_key().verify(sig, payload, ec.ECDSA(hashes.SHA256()))
        except Exception:
            verified = False
        sign_ms = (time.perf_counter() - t0) * 1000
        result["signing"] = {"ok": verified, "elapsed_ms": round(sign_ms, 3)}

    result["hndl_exposure"] = compare_rail(rail)[path if path == "hybrid_pqc" else "classical"]
    metrics.record_payment(rail, path, result["handshake"]["elapsed_ms"], result["signing"]["elapsed_ms"])
    return result
