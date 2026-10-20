"""Reproduce the retained biochemical and qPCR comparison calculations.

Run beside the supplementary CSV and JSON files with Python, NumPy and SciPy.
Input order is a source traceability label, not an animal identifier.
The script checks numerical calculations; it does not validate assays or identity.
"""
import csv
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).resolve().parent
GROUPS = ["Sham-operated", "Model", "Restoration"]


def read_csv(name):
    with (BASE / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def games_howell(arrays):
    result = []
    for i, j in combinations(range(3), 2):
        x, y = arrays[i], arrays[j]
        vx, vy = np.var(x, ddof=1) / len(x), np.var(y, ddof=1) / len(y)
        se2 = vx + vy
        df = se2**2 / (vx**2 / (len(x) - 1) + vy**2 / (len(y) - 1))
        difference = np.mean(x) - np.mean(y)
        q = abs(difference) / np.sqrt(se2 / 2)
        half = stats.studentized_range.ppf(0.95, 3, df) * np.sqrt(se2 / 2)
        result.append({"group_1": GROUPS[i], "group_2": GROUPS[j],
                       "difference": float(difference),
                       "CI95_low": float(difference - half),
                       "CI95_high": float(difference + half),
                       "p_adjusted": float(stats.studentized_range.sf(q, 3, df))})
    return result


def main():
    bio = read_csv("Supplementary_Data_1_Biochemical_Values.csv")
    panel = read_csv("Supplementary_Data_3_Original_qPCR_Panel.csv")
    saved = json.loads((BASE / "Supplementary_Statistical_Results.json").read_text())
    output = {"biochemical": {}, "qPCR_18_test_family": []}
    for endpoint in ["SOD", "MDA", "ROS"]:
        arrays = [np.array([float(r["Processed_value"]) for r in bio
                            if r["Endpoint"] == endpoint and r["Group"] == group])
                  for group in GROUPS]
        assert all(len(x) == 6 for x in arrays)
        omnibus = stats.f_oneway(*arrays, equal_var=False)
        pairwise = games_howell(arrays)
        for new in pairwise:
            old = next(r for r in saved["biochemical"]["posthoc"]
                       if r["endpoint"] == endpoint
                       and r["group_1"] == new["group_1"]
                       and r["group_2"] == new["group_2"])
            assert np.isclose(new["p_adjusted"], old["p_adjusted"], rtol=1e-6, atol=1e-10)
            assert np.isclose(new["CI95_low"], old["CI95_low"], atol=1e-8)
            assert np.isclose(new["CI95_high"], old["CI95_high"], atol=1e-8)
        output["biochemical"][endpoint] = {
            "F": float(omnibus.statistic), "p": float(omnibus.pvalue),
            "pairwise": pairwise}

    for target in ["AT1-R", "Nox1", "Nox4", "RhoA", "ROCK1", "ROCK2"]:
        data = {g: np.array([float(r["Target_Cq"]) - float(r["Paired_Actb_Cq"])
                             for r in panel if r["Recorded_target"] == target and r["Group"] == g])
                for g in GROUPS}
        assert all(len(x) == 6 for x in data.values())
        for numerator, denominator in [("Model", "Sham-operated"),
                                       ("Restoration", "Sham-operated"),
                                       ("Restoration", "Model")]:
            t = stats.ttest_ind(data[numerator], data[denominator], equal_var=False)
            output["qPCR_18_test_family"].append({
                "target": target, "numerator": numerator, "denominator": denominator,
                "t": float(t.statistic), "df": float(t.df), "p_raw": float(t.pvalue)})

    comparisons = output["qPCR_18_test_family"]
    order = np.argsort([r["p_raw"] for r in comparisons])
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (18 - rank) * comparisons[index]["p_raw"])
        comparisons[index]["p_holm"] = min(1.0, running)
    for new in comparisons:
        old = next(r for r in saved["qPCR"]["comparisons"]
                   if r["gene"] == new["target"]
                   and r["numerator_group"] == new["numerator"]
                   and r["denominator_group"] == new["denominator"])
        assert np.isclose(new["p_holm"], old["p_holm_18_test_family"], rtol=1e-6, atol=1e-10)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
