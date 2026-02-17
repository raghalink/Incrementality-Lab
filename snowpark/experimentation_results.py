import math
import scipy
from scipy.stats import norm

Z_95 = 1.96

DB = "AB_DB"
SCHEMA = "ANALYTICS"
INPUT_TABLE = f"{DB}.{SCHEMA}.MART_EXP_RESULTS_INPUT"
OUTPUT_TABLE = f"{DB}.{SCHEMA}.MART_EXP_EXPERIMENT_RESULTS_FINAL"

DEFAULT_PRACTICAL_THRESHOLD_ABS = 0.0010
DEFAULT_GUARDRAIL_VISIT_FLOOR_ABS = -0.0020


def req_int(row: dict, key: str) -> int:
    v = row.get(key)
    if v is None:
        raise ValueError(f"Missing required field: {key}")
    return int(v)


def opt_float(row: dict, key: str, default=None):
    v = row.get(key)
    return default if v is None else float(v)


def diff_in_proportions(n_c: int, x_c: int, n_t: int, x_t: int):
    if n_c <= 0 or n_t <= 0:
        raise ValueError(f"Invalid sample sizes: n_control={n_c}, n_treatment={n_t}")

    p_c = x_c / n_c
    p_t = x_t / n_t
    lift = p_t - p_c

    se = math.sqrt((p_t * (1 - p_t)) / n_t + (p_c * (1 - p_c)) / n_c)
    if se == 0:
        return {
            "control_rate": p_c,
            "treatment_rate": p_t,
            "lift": lift,
            "se": 0.0,
            "z": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "degenerate_ok": (lift == 0),
        }

    z = lift / se
    ci_lower = lift - Z_95 * se
    ci_upper = lift + Z_95 * se
    p_value = float(2 * (1 - norm.cdf(abs(z))))

    return {
        "control_rate": p_c,
        "treatment_rate": p_t,
        "lift": lift,
        "se": se,
        "z": z,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "degenerate_ok": True,
    }


def ci_significance(ci_lower, ci_upper):
    if ci_lower is None or ci_upper is None:
        return None
    return bool((ci_lower > 0) or (ci_upper < 0))


def decide(
    srm_status,
    balance_status,
    lift,
    ci_lower,
    guardrail_lift,
    min_practical_lift,
    min_visit_floor,
    degenerate_ok=True,
):
    srm = (srm_status or "").lower()
    bal = (balance_status or "").lower()

    if not degenerate_ok:
        return "Investigate Data", "Degenerate variance detected (SE=0 with non-zero lift)."

    if srm == "fail" or bal == "fail":
        return "Investigate Data", "Validity check failed (SRM or balance)."

    if guardrail_lift is not None and guardrail_lift < min_visit_floor:
        return "Do Not Roll Out", "Visit rate guardrail breached."

    if lift is None or lift < min_practical_lift:
        return "Do Not Roll Out", "Below minimum practical lift."

    # Keep your original evidence gate (CI > 0) OR strengthen to CI >= MPL
    # Here: CI >= MPL (more aligned to your newer policy). If you want the old rule, change to: ci_lower > 0
    if ci_lower is not None and ci_lower >= min_practical_lift:
        return "Roll Out", "Confident lift clears minimum practical threshold."

    return "Run Follow-up", "Uncertain impact; recommend follow-up experiment."


def main(session):
    rows = session.table(INPUT_TABLE).collect()
    if len(rows) != 1:
        raise ValueError(f"Expected exactly 1 row in {INPUT_TABLE}, found {len(rows)}")

    r = rows[0].as_dict()

    experiment_id = r.get("EXPERIMENT_ID")
    analysis_type = r.get("ANALYSIS_TYPE") or "ITT"
    segment_name = r.get("SEGMENT_NAME") or "ALL"

    n_c = req_int(r, "N_CONTROL")
    n_t = req_int(r, "N_TREATMENT")
    x_c = req_int(r, "CONV_CONTROL")
    x_t = req_int(r, "CONV_TREATMENT")
    v_c = req_int(r, "VISIT_CONTROL")
    v_t = req_int(r, "VISIT_TREATMENT")

    exposure_rate = opt_float(r, "EXPOSURE_RATE_TREATMENT", default=None)
    srm_status = r.get("SRM_STATUS")
    balance_status = r.get("BALANCE_STATUS")

    min_practical_lift = opt_float(r, "PRACTICAL_THRESHOLD_ABS", default=DEFAULT_PRACTICAL_THRESHOLD_ABS)
    min_visit_floor = opt_float(r, "GUARDRAIL_VISIT_FLOOR_ABS", default=DEFAULT_GUARDRAIL_VISIT_FLOOR_ABS)

    stats = diff_in_proportions(n_c, x_c, n_t, x_t)

    vr_c = v_c / n_c
    vr_t = v_t / n_t
    visit_lift = vr_t - vr_c

    lift_rel = None if stats["control_rate"] == 0 else (stats["lift"] / stats["control_rate"])
    visit_lift_rel = None if vr_c == 0 else (visit_lift / vr_c)

    practical_pass = stats["lift"] >= min_practical_lift
    guardrail_pass = visit_lift >= min_visit_floor

    sig_flag = ci_significance(stats["ci_lower"], stats["ci_upper"])

    decision, decision_reason = decide(
        srm_status=srm_status,
        balance_status=balance_status,
        lift=stats["lift"],
        ci_lower=stats["ci_lower"],
        guardrail_lift=visit_lift,
        min_practical_lift=min_practical_lift,
        min_visit_floor=min_visit_floor,
        degenerate_ok=stats["degenerate_ok"],
    )

    out_row = {
        # Identifiers
        "EXPERIMENT_ID": experiment_id,
        "ANALYSIS_TYPE": analysis_type,
        "SEGMENT": segment_name,
        "METRIC": "Conversion Rate",

        # Sample sizes & raw counts
        "CONTROL_USERS": n_c,
        "TREATMENT_USERS": n_t,
        "CONTROL_CONVERSIONS": x_c,
        "TREATMENT_CONVERSIONS": x_t,
        "CONTROL_VISITS": v_c,
        "TREATMENT_VISITS": v_t,

        # Rates
        "CONTROL_CONVERSION_RATE": stats["control_rate"],
        "TREATMENT_CONVERSION_RATE": stats["treatment_rate"],
        "CONTROL_VISIT_RATE": vr_c,
        "TREATMENT_VISIT_RATE": vr_t,
        "TREATMENT_EXPOSURE_RATE": exposure_rate,

        # Effects
        "CONVERSION_LIFT": stats["lift"],
        "CONVERSION_LIFT_RELATIVE": lift_rel,
        "VISIT_LIFT": visit_lift,
        "VISIT_LIFT_RELATIVE": visit_lift_rel,

        # Uncertainty
        "STANDARD_ERROR": stats["se"],
        "Z_SCORE": stats["z"],
        "CI_LOWER": stats["ci_lower"],
        "CI_UPPER": stats["ci_upper"],
        "P_VALUE": stats["p_value"],
        "SIGNIFICANT": sig_flag,

        # Validity + thresholds + pass flags
        "SRM_STATUS": (srm_status or "").lower(),
        "BALANCE_STATUS": (balance_status or "").lower(),
        "MIN_PRACTICAL_LIFT": min_practical_lift,
        "MIN_VISIT_LIFT_FLOOR": min_visit_floor,
        "PRACTICAL_PASS": practical_pass,
        "GUARDRAIL_PASS": guardrail_pass,

        # Decision
        "DECISION": decision,
        "DECISION_REASON": decision_reason,
    }

    out_df = session.create_dataframe([out_row])
    out_df.write.mode("overwrite").save_as_table(OUTPUT_TABLE)
    return out_df