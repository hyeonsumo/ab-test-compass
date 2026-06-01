import hashlib
import secrets


def assign_variant(user_id: str, experiment_salt: str, variant_a_ratio: float) -> str:
    """
    Deterministically assign a user_id to A or B.
    Same user_id + salt always returns the same result.
    """
    key = f"{user_id}:{experiment_salt}"
    hash_int = int(hashlib.md5(key.encode()).hexdigest(), 16)
    bucket = (hash_int % 10000) / 10000
    return "A" if bucket < variant_a_ratio else "B"


def generate_salt() -> str:
    return secrets.token_hex(8)
