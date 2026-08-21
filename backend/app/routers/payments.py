from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.payment_gateway import process_payment

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentRequest(BaseModel):
    rail: str = "fedwire"
    originator: str
    beneficiary: str
    amount_usd: float
    reference: str = ""
    path: str = "hybrid_pqc"  # "classical" or "hybrid_pqc"


@router.post("/process")
def process(req: PaymentRequest):
    try:
        return process_payment(req.rail, req.originator, req.beneficiary, req.amount_usd, req.reference, req.path)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/compare")
def compare(req: PaymentRequest):
    """Runs the SAME message down both paths for a side-by-side comparison."""
    classical = process_payment(req.rail, req.originator, req.beneficiary, req.amount_usd, req.reference, "classical")
    hybrid = process_payment(req.rail, req.originator, req.beneficiary, req.amount_usd, req.reference, "hybrid_pqc")
    return {"classical": classical, "hybrid_pqc": hybrid}
