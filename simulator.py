import random
from datetime import datetime

import storage
from assignment import assign_variant


def simulate_traffic(
    experiment: dict,
    num_users: int,
    seed: int = None,
    progress_callback=None,
) -> dict:
    """
    Simulate traffic for one experiment.

    For each synthetic user:
    1. Assign A/B via deterministic hashing.
    2. Write one exposure event.
    3. Write a conversion event based on the variant conversion rate.
    """
    if seed is not None:
        random.seed(seed)

    salt = experiment["salt"]
    ratio = experiment["variant_a_ratio"]
    baseline = experiment["baseline_rate"]
    effect = experiment["treatment_effect"]

    rate_a = baseline
    rate_b = baseline * (1 + effect)

    existing = storage.load_exposures(experiment["id"])
    start_idx = len(existing)

    exposure_rows = []
    conversion_rows = []
    converted_variant_counts = {"A": 0, "B": 0}
    timestamp = datetime.now().isoformat(timespec="seconds")

    for i in range(num_users):
        user_id = f"sim_user_{start_idx + i}"
        variant = assign_variant(user_id, salt, ratio)

        exposure_rows.append(
            {
                "experiment_id": experiment["id"],
                "user_id": user_id,
                "variant": variant,
                "timestamp": timestamp,
            }
        )

        conv_rate = rate_a if variant == "A" else rate_b
        if random.random() < conv_rate:
            conversion_rows.append(
                {
                    "experiment_id": experiment["id"],
                    "user_id": user_id,
                    "timestamp": timestamp,
                }
            )
            converted_variant_counts[variant] += 1

        if progress_callback and (i + 1) % max(1, num_users // 100) == 0:
            progress_callback((i + 1) / num_users)

    storage.append_exposures(exposure_rows)
    storage.append_conversions(conversion_rows)

    return {
        "exposures": len(exposure_rows),
        "conversions_a": converted_variant_counts["A"],
        "conversions_b": converted_variant_counts["B"],
    }
