"""Reproduce RVLM statistics from the supplied processed values.

Usage: python reproduce_rvlm_statistics.py S1_Data_RVLM_Processed_Values.csv OUTPUT.json
This script verifies calculations. It does not validate animal identities,
original instrument records, assay calibration or study eligibility.
"""
import csv
import json
import math
import platform
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import scipy
from scipy import stats

GROUPS = ["Sham-operated", "Model", "Restoration"]


def analyze(source):
    rows = list(csv.DictReader(Path(source).open(encoding="utf-8-sig")))
    output = {"software": {"Python": platform.python_version(),
              "NumPy": np.__version__, "SciPy": scipy.__version__},
              "source": Path(source).name,
              "scope": "Processed RVLM values for the three declared groups only",
              "experimental_unit": "Independent rat, subject to source-record confirmation",
              "animal_identifiers": "Observation order is not an animal identifier",
              "multiple_testing": "Three pairwise contrasts within each endpoint; no adjustment across endpoints",
              "confidence_intervals": "95% Games-Howell intervals within each endpoint",
              "summaries": [], "omnibus": [], "posthoc": [], "assumptions": []}
    for metric in ["SOD", "MDA", "ROS"]:
        arrays = {g: np.array([float(r["Processed_value"]) for r in rows
                  if r["Endpoint"] == metric and r["Group"] == g]) for g in GROUPS}
        for g, a in arrays.items():
            if len(a) != 6 or not np.isfinite(a).all():
                raise ValueError(f"Expected six finite supplied values for {metric}/{g}")
            unit = next(r["Unit"] for r in rows if r["Endpoint"] == metric)
            output["summaries"].append({"endpoint": metric, "group": g, "n": len(a),
                 "mean": float(a.mean()), "sd": float(a.std(ddof=1)), "unit": unit})
            sw = stats.shapiro(a)
            output["assumptions"].append({"endpoint": metric, "group": g,
                 "test": "Shapiro-Wilk", "statistic": float(sw.statistic), "p": float(sw.pvalue)})
        aa = list(arrays.values())
        n = np.array([len(a) for a in aa], dtype=float)
        means = np.array([a.mean() for a in aa])
        variances = np.array([a.var(ddof=1) for a in aa])
        w = n / variances
        k = len(aa)
        weighted_mean = np.sum(w * means) / w.sum()
        b = np.sum((1 - w / w.sum())**2 / (n - 1))
        f = np.sum(w * (means - weighted_mean)**2) / (k - 1)
        f /= 1 + 2 * (k - 2) * b / (k*k - 1)
        df2 = (k*k - 1) / (3 * b)
        output["omnibus"].append({"endpoint": metric, "test": "Welch one-way ANOVA",
               "F": float(f), "df1": k - 1, "df2": float(df2),
               "p": float(stats.f.sf(f, k - 1, df2)), "n_total": int(n.sum())})
        for g1, g2 in combinations(GROUPS, 2):
            a1, a2 = arrays[g1], arrays[g2]
            v1, v2 = a1.var(ddof=1)/len(a1), a2.var(ddof=1)/len(a2)
            df = (v1 + v2)**2 / (v1*v1/(len(a1)-1) + v2*v2/(len(a2)-1))
            delta = float(a1.mean() - a2.mean())
            se_q = math.sqrt((v1 + v2)/2)
            q = abs(delta) / se_q
            half = float(stats.studentized_range.ppf(0.95, k, df)) * se_q
            output["posthoc"].append({"endpoint": metric, "group_1": g1, "group_2": g2,
                "difference_group_1_minus_group_2": delta, "CI95_low": delta-half,
                "CI95_high": delta+half, "q": q, "df": df,
                "p_adjusted": float(stats.studentized_range.sf(q, k, df)),
                "n_1": len(a1), "n_2": len(a2)})
    return output


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    result = analyze(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Reproduced summaries, Welch tests and Games-Howell comparisons for three RVLM endpoints.")
