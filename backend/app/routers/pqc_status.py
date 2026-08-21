from fastapi import APIRouter

from ..pqc import hybrid_kex, signing

router = APIRouter(prefix="/pqc", tags=["pqc"])


@router.get("/selftest")
def selftest():
    """Hit this FIRST after `docker compose up --build`. If pqcrypto's real
    installed API differs from what hybrid_kex.py/signing.py assume, this
    will show the exact error rather than failing silently mid-payment."""
    return {
        "pqcrypto_available": hybrid_kex.PQCRYPTO_AVAILABLE,
        "hybrid_kex": hybrid_kex.selftest(),
        "signing": signing.selftest(),
    }
