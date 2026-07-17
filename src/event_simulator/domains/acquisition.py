"""Application and KYC lifecycle (family: application_kyc_account)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

CHANNELS = ["organic", "paid_social", "paid_search", "referral", "partnership"]
CHANNEL_WEIGHTS = [0.45, 0.20, 0.15, 0.15, 0.05]
KYC_DECISIONS = ["approved", "rejected", "manual_review"]
KYC_WEIGHTS = [0.90, 0.07, 0.03]


@dataclass
class Journey:
    sequence: int
    customer_id: str
    application_id: str
    account_id: str
    referral_id: str | None
    referrer_customer_id: str | None
    channel: str
    applied_at: datetime
    kyc_decision: str
    activated_at: datetime | None = None

    @property
    def referred(self) -> bool:
        return self.referral_id is not None

    @property
    def trace(self) -> str:
        return f"journey:{self.customer_id}"


def generate(config, emitter, ids, rng, sequence: int, journey_start) -> Journey:
    customer_id = ids.customer_id(sequence)
    application_id = ids.application_id(sequence)
    channel = rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
    referred = channel == "referral"
    referral_id = ids.referral_id(sequence) if referred else None
    referrer = ids.customer_id(config.customers + sequence) if referred else None

    journey = Journey(
        sequence=sequence,
        customer_id=customer_id,
        application_id=application_id,
        account_id=ids.account_id(sequence),
        referral_id=referral_id,
        referrer_customer_id=referrer,
        channel=channel,
        applied_at=journey_start,
        kyc_decision=rng.choices(KYC_DECISIONS, weights=KYC_WEIGHTS, k=1)[0],
    )

    emitter.emit(
        "application-submitted",
        1,
        business_key=f"app:{application_id}",
        occurred=journey.applied_at,
        payload={
            "application_id": application_id,
            "customer_id": customer_id,
            "channel": channel,
            "campaign_id": "cmp_spring_boost" if channel.startswith("paid") else None,
            "referral_id": referral_id,
            "requested_product": "current_account",
        },
        trace=journey.trace,
    )
    emitter.emit(
        "kyc-decisioned",
        1,
        business_key=f"kyc:{application_id}",
        occurred=journey.applied_at + timedelta(minutes=rng.randrange(5, 120)),
        payload={
            "application_id": application_id,
            "customer_id": customer_id,
            "decision": journey.kyc_decision,
            "decision_source": "automated" if rng.random() < 0.95 else "manual",
        },
        trace=journey.trace,
    )
    return journey
