from datetime import datetime
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

EXPERIMENTS_CSV = DATA_DIR / "experiments.csv"
EXPOSURES_CSV = DATA_DIR / "exposures.csv"
CONVERSIONS_CSV = DATA_DIR / "conversions.csv"

EXPERIMENT_COLS = [
    "id",
    "name",
    "hypothesis",
    "salt",
    "variant_a_ratio",
    "baseline_rate",
    "treatment_effect",
    "duration_days",
    "status",
    "created_at",
]
EXPOSURE_COLS = ["experiment_id", "user_id", "variant", "timestamp"]
CONVERSION_COLS = ["experiment_id", "user_id", "timestamp"]


def _ensure_file(path: Path, columns: list):
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)
        return

    df = pd.read_csv(path)
    changed = False
    for column in columns:
        if column not in df.columns:
            df[column] = ""
            changed = True

    if changed:
        df = df[columns]
        df.to_csv(path, index=False)


def init_storage():
    _ensure_file(EXPERIMENTS_CSV, EXPERIMENT_COLS)
    _ensure_file(EXPOSURES_CSV, EXPOSURE_COLS)
    _ensure_file(CONVERSIONS_CSV, CONVERSION_COLS)


def load_experiments() -> pd.DataFrame:
    return pd.read_csv(EXPERIMENTS_CSV)


def create_experiment(
    name,
    salt,
    variant_a_ratio,
    baseline_rate,
    treatment_effect,
    hypothesis="",
    duration_days=14,
) -> int:
    df = load_experiments()
    new_id = int(df["id"].max()) + 1 if len(df) > 0 else 1
    new_row = {
        "id": new_id,
        "name": name,
        "hypothesis": hypothesis,
        "salt": salt,
        "variant_a_ratio": variant_a_ratio,
        "baseline_rate": baseline_rate,
        "treatment_effect": treatment_effect,
        "duration_days": duration_days,
        "status": "running",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(EXPERIMENTS_CSV, index=False)
    return new_id


def get_experiment(exp_id: int):
    df = load_experiments()
    row = df[df["id"] == exp_id]
    return row.iloc[0].to_dict() if len(row) > 0 else None


def append_exposures(rows: list[dict]):
    """Append exposure events in a batch."""
    if not rows:
        return
    df = pd.DataFrame(rows)
    df.to_csv(EXPOSURES_CSV, mode="a", header=False, index=False)


def append_conversions(rows: list[dict]):
    """Append conversion events in a batch."""
    if not rows:
        return
    df = pd.DataFrame(rows)
    df.to_csv(CONVERSIONS_CSV, mode="a", header=False, index=False)


def load_exposures(experiment_id: int = None) -> pd.DataFrame:
    df = pd.read_csv(EXPOSURES_CSV)
    if experiment_id is not None:
        df = df[df["experiment_id"] == experiment_id]
    return df


def load_conversions(experiment_id: int = None) -> pd.DataFrame:
    df = pd.read_csv(CONVERSIONS_CSV)
    if experiment_id is not None:
        df = df[df["experiment_id"] == experiment_id]
    return df


def get_summary(experiment_id: int) -> dict:
    """Return exposure and conversion metrics by variant."""
    exposures = load_exposures(experiment_id)
    conversions = load_conversions(experiment_id)

    summary = {
        "A": {"exposures": 0, "conversions": 0, "rate": 0.0},
        "B": {"exposures": 0, "conversions": 0, "rate": 0.0},
    }

    if len(exposures) == 0:
        return summary

    exp_counts = exposures["variant"].value_counts().to_dict()
    summary["A"]["exposures"] = int(exp_counts.get("A", 0))
    summary["B"]["exposures"] = int(exp_counts.get("B", 0))

    if len(conversions) > 0:
        user_variant = exposures.set_index("user_id")["variant"].to_dict()
        conversions = conversions.copy()
        conversions["variant"] = conversions["user_id"].map(user_variant)
        conv_counts = conversions["variant"].value_counts().to_dict()
        summary["A"]["conversions"] = int(conv_counts.get("A", 0))
        summary["B"]["conversions"] = int(conv_counts.get("B", 0))

    for variant in ["A", "B"]:
        if summary[variant]["exposures"] > 0:
            summary[variant]["rate"] = (
                summary[variant]["conversions"] / summary[variant]["exposures"]
            )

    return summary


def delete_experiment(exp_id: int) -> bool:
    """Delete an experiment and all related exposure/conversion events."""
    df = load_experiments()
    if exp_id not in df["id"].values:
        return False

    df = df[df["id"] != exp_id]
    df.to_csv(EXPERIMENTS_CSV, index=False)

    exposures = pd.read_csv(EXPOSURES_CSV)
    exposures = exposures[exposures["experiment_id"] != exp_id]
    exposures.to_csv(EXPOSURES_CSV, index=False)

    conversions = pd.read_csv(CONVERSIONS_CSV)
    conversions = conversions[conversions["experiment_id"] != exp_id]
    conversions.to_csv(CONVERSIONS_CSV, index=False)

    return True


def reset_all():
    """Delete all experiment and event data while preserving config.json."""
    EXPERIMENTS_CSV.unlink(missing_ok=True)
    EXPOSURES_CSV.unlink(missing_ok=True)
    CONVERSIONS_CSV.unlink(missing_ok=True)
    init_storage()


def has_any_experiment() -> bool:
    return len(load_experiments()) > 0


def seed_sample_data():
    """Seed one sample experiment with synthetic events on first setup."""
    from assignment import generate_salt
    from simulator import simulate_traffic

    if has_any_experiment():
        return

    sample = {
        "name": "샘플: 결제 버튼 색상 테스트",
        "salt": generate_salt(),
        "variant_a_ratio": 0.5,
        "baseline_rate": 0.10,
        "treatment_effect": 0.08,
        "hypothesis": "결제 버튼 색상을 변경하면 결제 전환율이 개선될 것이다.",
        "duration_days": 14,
    }
    exp_id = create_experiment(**sample)

    experiment = {
        "id": exp_id,
        "salt": sample["salt"],
        "variant_a_ratio": sample["variant_a_ratio"],
        "baseline_rate": sample["baseline_rate"],
        "treatment_effect": sample["treatment_effect"],
    }
    simulate_traffic(experiment, 10_000, seed=42)
