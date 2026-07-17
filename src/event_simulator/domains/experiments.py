"""Experiment assignment (family: experiment)."""

EXPERIMENT_ID = "exp_onboarding_v2"


def generate(config, emitter, ids, rng, journey) -> None:
    if rng.random() >= 0.5:
        return
    emitter.emit(
        "experiment-assigned",
        1,
        business_key=f"assign:{EXPERIMENT_ID}:{journey.customer_id}",
        occurred=journey.applied_at,
        payload={
            "experiment_id": EXPERIMENT_ID,
            "customer_id": journey.customer_id,
            "variant": "treatment" if rng.random() < 0.5 else "control",
            "assignment_unit": "customer",
        },
        trace=journey.trace,
    )
