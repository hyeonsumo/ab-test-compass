import math

from scipy import stats


def analyze_experiment(
    a_total: int,
    a_converted: int,
    b_total: int,
    b_converted: int,
    alpha: float = 0.05,
) -> dict:
    """
    Analyze the conversion-rate difference between two groups using a pooled z-test.
    """
    if a_total == 0 or b_total == 0:
        return {"error": "표본 크기가 0인 그룹이 있습니다."}

    p_a = a_converted / a_total
    p_b = b_converted / b_total
    diff = p_b - p_a

    p_pool = (a_converted + b_converted) / (a_total + b_total)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / a_total + 1 / b_total))

    if se_pool == 0:
        return {"error": "표준 오차가 0입니다. 표본이 너무 작거나 전환이 전혀 없습니다."}

    z = diff / se_pool
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    se_diff = math.sqrt(p_a * (1 - p_a) / a_total + p_b * (1 - p_b) / b_total)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff

    lift = diff / p_a if p_a > 0 else 0

    return {
        "rate_a": p_a,
        "rate_b": p_b,
        "diff": diff,
        "lift": lift,
        "p_value": p_value,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "significant": p_value < alpha,
        "z_score": z,
        "alpha": alpha,
    }


def check_srm(
    a_total: int,
    b_total: int,
    expected_a_ratio: float = 0.5,
    threshold: float = 0.001,
) -> dict:
    """
    Check Sample Ratio Mismatch with a chi-square test.
    """
    total = a_total + b_total
    if total == 0:
        return {"has_srm": False, "p_value": 1.0, "actual_a_ratio": 0}

    expected_a = total * expected_a_ratio
    expected_b = total * (1 - expected_a_ratio)

    if expected_a == 0 or expected_b == 0:
        return {
            "has_srm": False,
            "p_value": 1.0,
            "actual_a_ratio": a_total / total,
        }

    chi2 = ((a_total - expected_a) ** 2 / expected_a) + (
        (b_total - expected_b) ** 2 / expected_b
    )
    p_value = 1 - stats.chi2.cdf(chi2, df=1)

    return {
        "chi2": chi2,
        "p_value": p_value,
        "has_srm": p_value < threshold,
        "actual_a_ratio": a_total / total,
        "expected_a_ratio": expected_a_ratio,
    }


def required_sample_size(
    baseline: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int | None:
    """
    Calculate required sample size per group for detecting a relative MDE.
    """
    p2 = baseline * (1 + mde)
    if baseline <= 0 or baseline >= 1 or mde == 0 or p2 <= 0 or p2 > 1:
        return None

    p1 = baseline
    p_avg = (p1 + p2) / 2

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    n = (
        (
            z_alpha * math.sqrt(2 * p_avg * (1 - p_avg))
            + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        )
        ** 2
    ) / ((p2 - p1) ** 2)

    return int(math.ceil(n))
