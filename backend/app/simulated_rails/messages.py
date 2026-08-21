"""Simulated payment-rail message structures. Loosely modeled on the fields
that actually matter for FedWire (real-time gross settlement), CHIPS
(net settlement), and ACH (batch) messages — enough structure to carry
real cryptographic operations for the demo without implementing anything
resembling the real message formats (ISO 20022, NACHA file spec, etc.)."""
import uuid
import datetime
from dataclasses import dataclass, asdict


@dataclass
class PaymentMessage:
    message_id: str
    rail: str  # "fedwire" | "chips" | "ach"
    originator: str
    beneficiary: str
    amount_usd: float
    settlement_date: str
    reference: str

    def to_bytes(self) -> bytes:
        import json
        return json.dumps(asdict(self), sort_keys=True).encode()


def build_fedwire_message(originator: str, beneficiary: str, amount_usd: float, reference: str) -> PaymentMessage:
    return PaymentMessage(
        message_id=str(uuid.uuid4()),
        rail="fedwire",
        originator=originator,
        beneficiary=beneficiary,
        amount_usd=amount_usd,
        settlement_date=datetime.datetime.utcnow().date().isoformat(),
        reference=reference,
    )


def build_chips_message(originator: str, beneficiary: str, amount_usd: float, reference: str) -> PaymentMessage:
    return PaymentMessage(
        message_id=str(uuid.uuid4()),
        rail="chips",
        originator=originator,
        beneficiary=beneficiary,
        amount_usd=amount_usd,
        settlement_date=(datetime.datetime.utcnow() + datetime.timedelta(days=1)).date().isoformat(),
        reference=reference,
    )


def build_ach_message(originator: str, beneficiary: str, amount_usd: float, reference: str) -> PaymentMessage:
    return PaymentMessage(
        message_id=str(uuid.uuid4()),
        rail="ach",
        originator=originator,
        beneficiary=beneficiary,
        amount_usd=amount_usd,
        settlement_date=(datetime.datetime.utcnow() + datetime.timedelta(days=2)).date().isoformat(),
        reference=reference,
    )


BUILDERS = {"fedwire": build_fedwire_message, "chips": build_chips_message, "ach": build_ach_message}
