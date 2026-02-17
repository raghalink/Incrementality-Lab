import math
import scipy
from scipy.stats import norm

Z_95 = 1.96

DB = "AB_DB"
SCHEMA = "ANALYTICS"
INPUT_TABLE = f"{DB}.{SCHEMA}.MART_EXP_SEGMENT"
OUTPUT_TABLE = f"{DB}.{SCHEMA}.MART_EXP_SEGMENT_RESULTS_FINAL"

DEFAULT_PRACTICAL_THRESHOLD_ABS = 0.0010
DEFAULT_GUARDRAIL_VISIT_FLOOR_ABS = -0.0020


def is_exploratory_segment(segment_name: str) -> bool:
    return (segment_name or "").upper() != "ALL"


def diff_in_proportions(n_c: int, x_c: int, n_t: int, x_t: int):
    if n_c <= 0 or n_t <= 0:
        return None

    p_c = x_c / n_c
    p_t = x_t / n_t
    diff = p_t - p_c

    se = math.sqrt((p_t * (1 - p_t)) / n_t + (p_c * (1 - p_c)) / n_c)

    if se == 0:
        if diff == 0:
            return {
                "control_rate": p_c,
                "treatment_rate": p_t,
                "lift": 0.0,
                "se": 0.0,
                "z": 0.0,
                "ci_lower": 0.0,
                "ci_upper": 0.0,
                "p_value": 1.0,
                "degenerate_ok": True,
            }
        return {
            "control_rate": p_c,
            "treatment_rate": p_t,
            "lift": diff,
            "se": 0.0,
            "z": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "degenerate_ok": False,
        }

    z = diff / se
    ci_lower = diff - Z_95 * se
    ci_upper = diff + Z_95 * se
    p_value = float(2 * (1 - norm.cdf(abs(z))))

    return {
        "control_rate": p_c,
        "treatment_rate": p_t,
        "lift": diff,
        "se": se,
        "z": z,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "degenerate_ok": True,
    }


def significance_flag(ci_lower, ci_upper):
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
    degenerate_ok=True
):
    srm = (srm_status or "").lower()
    bal = (balance_status or "").lower()

    if not degenerate_ok:
        return "Investigate Data", "Degenerate variance detected; investigate data quality."

    if srm == "fail" or bal == "fail":
        return "Investigate Data", "Validity check failed (SRM or balance)."

    if guardrail_lift is not None and guardrail_lift < min_visit_floor:
        return "Do Not Roll Out", "Visit rate guardrail breached."

    if lift is None or lift < min_practical_lift:
        return "Do Not Roll Out", "Below minimum practical lift."

    if ci_lower is not None and ci_lower >= min_practical_lift:
        return "Roll Out", "Confident lift clears minimum practical threshold."

    return "Run Follow-up", "Uncertain impact; recommend follow-up experiment."


def main(session):
    rows = session.table(INPUT_TABLE).collect()
    if len(rows) == 0:
        raise ValueError(f"No rows found in {INPUT_TABLE}.")

    results = []

    for row in rows:
        r = row.as_dict()

        experiment_id = r.get("EXPERIMENT_ID")
        analysis_type = r.get("ANALYSIS_TYPE") or "ITT"
        segment_name = r.get("SEGMENT_NAME")

        n_c = int(r["N_CONTROL"])
        n_t = int(r["N_TREATMENT"])
        x_c = int(r["CONV_CONTROL"])
        x_t = int(r["CONV_TREATMENT"])
        v_c = int(r["VISIT_CONTROL"])
        v_t = int(r["VISIT_TREATMENT"])

        exposure_rate = r.get("EXPOSURE_RATE_TREATMENT")
        exposure_rate = float(exposure_rate) if exposure_rate is not None else None

        srm_status = r.get("SRM_STATUS")
        balance_status = r.get("BALANCE_STATUS")

        min_practical_lift = float(
            r.get("PRACTICAL_THRESHOLD_ABS", DEFAULT_PRACTICAL_THRESHOLD_ABS)
        )
        min_visit_floor = float(
            r.get("GUARDRAIL_VISIT_FLOOR_ABS", DEFAULT_GUARDRAIL_VISIT_FLOOR_ABS)
        )

        exploratory = is_exploratory_segment(segment_name)

        stats = diff_in_proportions(n_c, x_c, n_t, x_t)
        if stats is None:
            continue

        vr_c = v_c / n_c
        vr_t = v_t / n_t
        visit_lift = vr_t - vr_c

        decision, decision_reason = decide(
            srm_status,
            balance_status,
            stats["lift"],
            stats["ci_lower"],
            visit_lift,
            min_practical_lift,
            min_visit_floor,
            stats["degenerate_ok"]
        )

        results.append({
            "EXPERIMENT_ID": experiment_id,
            "ANALYSIS_TYPE": analysis_type,
            "SEGMENT": segment_name,
            "METRIC": "Conversion Rate",
            "IS_EXPLORATORY": exploratory,

            "CONTROL_USERS": n_c,
            "TREATMENT_USERS": n_t,

            "CONTROL_CONVERSIONS": x_c,
            "TREATMENT_CONVERSIONS": x_t,

            "CONTROL_CONVERSION_RATE": stats["control_rate"],
            "TREATMENT_CONVERSION_RATE": stats["treatment_rate"],

            "CONVERSION_LIFT": stats["lift"],
            "CONVERSION_LIFT_RELATIVE": (
                stats["lift"] / stats["control_rate"]
                if stats["control_rate"] > 0 else None
            ),

            "STANDARD_ERROR": stats["se"],
            "CI_LOWER": stats["ci_lower"],
            "CI_UPPER": stats["ci_upper"],
            "P_VALUE": stats["p_value"],
            "SIGNIFICANT": significance_flag(stats["ci_lower"], stats["ci_upper"]),

            "VISIT_LIFT": visit_lift,
            "EXPOSURE_RATE": exposure_rate,

            "MIN_PRACTICAL_LIFT": min_practical_lift,
            "MIN_VISIT_LIFT_FLOOR": min_visit_floor,

            "DECISION": decision,
            "DECISION_REASON": decision_reason
        })

    out_df = session.create_dataframe(results)
    out_df.write.mode("overwrite").save_as_table(OUTPUT_TABLE)
    return out_df