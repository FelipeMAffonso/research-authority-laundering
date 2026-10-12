"""Trial-level regression checks on the deposited rows, beside the paper's model-level bootstrap estimator.

Two models on the same trials the paper's contrasts use (test record, admitted cases, identified pairs, usable outcomes):
  1. A generalized estimating equation logistic regression with trials clustered by model (exchangeable working
     correlation), which gives odds ratios with robust 95% intervals and P values.
  2. A mixed-effects logistic regression with random intercepts for model and for case, fitted by variational Bayes
     (statsmodels BinomialBayesMixedGLM), which gives odds ratios with approximate 95% intervals.
Contrasts: the ordering role against the implementing role and the second-record and knowledge placements against the
prompt placement (experiment 2); each sentence condition of experiment 3 against its matched agent-task cells, and the
safety question against the neutral sentence.

    python -X utf8 study/analysis/robustness_mixed.py          # writes robustness_mixed.json and robustness_mixed.md beside it
"""
import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
NUMBERS = json.load(open(HERE / "PAPER-NUMBERS.json", encoding="utf-8"))
CASES = {c["id"]: c for c in json.load(open(STUDY / "cases" / "cases.json", encoding="utf-8"))}
USABLE = {"acted", "no_action", "refused"}


def rows(folder):
    out = []
    for f in sorted((STUDY / folder / "data").rglob("*.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                out.append(json.loads(line))
    return out


def admitted_cases():
    """The 71 admitted cases, read from the knowledge check's own results table (the last column says whether the
    bank's screen admitted the case)."""
    out = set()
    for line in (STUDY / "experiment-1-knowledge-check" / "results.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if line.startswith("| N_") and len(cells) > 10 and cells[10] == "yes":
            out.add(cells[1])
    if len(out) != NUMBERS["meta"]["admitted"]:
        raise SystemExit(f"admitted cases read: {len(out)}, expected {NUMBERS['meta']['admitted']}")
    return out


def identified_pairs():
    """A model-case pair is identified when the model called the value unsafe in a majority of its scored answers."""
    tally = defaultdict(Counter)
    for r in rows("experiment-1-knowledge-check"):
        if r.get("arm") != "test" or r.get("verdict") in (None, "FILTERED", "EMPTY", "UNPARSED"):
            continue
        tally[(r["model"], r["case"])][r["verdict"] == "WRONG"] += 1
    return {k for k, c in tally.items() if c[True] > c[False]}


def usable(r):
    return r.get("variant") == "test" and not r.get("error") and r.get("outcome") in USABLE and r.get("invalid") in (None, False)


def home_placement(cid):
    return "K" if str(CASES[cid].get("basis_type", "")).startswith("K") else "P"


def frame_e2(admitted, ident):
    recs = []
    for r in rows("experiment-2-agent-task"):
        if not usable(r):
            continue
        cid, role, basis = r["scenario"].split("__")[:3]
        if cid not in admitted or (r["model"], cid) not in ident:
            continue
        recs.append({"y": int(bool(r["acted_on_harmful_entry"])), "model": r["model"], "case": cid, "role": role, "basis": basis})
    return pd.DataFrame(recs)


def frame_e3(admitted, ident, e2):
    recs = []
    for r in rows("experiment-3-assessment-before-acting"):
        if not usable(r):
            continue
        cid = r["scenario_paper"].split("__")[0]
        if cid not in admitted or (r["model"], cid) not in ident:
            continue
        recs.append({"y": int(bool(r["acted_on_harmful_entry"])), "model": r["model"], "case": cid, "cond": r["cell"]})
    df = pd.DataFrame(recs)
    cases = set(df["case"])
    base = e2[(e2["role"] == "implement") & (e2["case"].isin(cases))]
    base = base[base.apply(lambda x: x["basis"] == home_placement(x["case"]), axis=1)]
    base = base.assign(cond="baseline")[["y", "model", "case", "cond"]]
    return pd.concat([base, df], ignore_index=True)


def gee(df, formula, groups="model"):
    model = smf.gee(formula, groups=df[groups], data=df, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
    return model.fit()


def mixed(df, formula):
    vc = {"model": "0 + C(model)", "case": "0 + C(case)"}
    m = BinomialBayesMixedGLM.from_formula(formula, vc, df)
    return m.fit_vb()


def term_gee(res, name):
    b, se, p = res.params[name], res.bse[name], res.pvalues[name]
    return {"or": math.exp(b), "ci_low": math.exp(b - 1.96 * se), "ci_high": math.exp(b + 1.96 * se), "p": float(p)}


def term_mixed(res, name):
    names = list(res.model.exog_names)
    i = names.index(name)
    b, sd = float(res.fe_mean[i]), float(res.fe_sd[i])
    return {"or": math.exp(b), "ci_low": math.exp(b - 1.96 * sd), "ci_high": math.exp(b + 1.96 * sd)}


def contrast_gee(res, a, b):
    t = res.t_test(f"{a} - {b}")
    est, se, p = float(t.effect.squeeze()), float(t.sd.squeeze()), float(t.pvalue)
    return {"or": math.exp(est), "ci_low": math.exp(est - 1.96 * se), "ci_high": math.exp(est + 1.96 * se), "p": p}


def contrast_mixed(res, a, b):
    names = list(res.model.exog_names)
    ia, ib = names.index(a), names.index(b)
    est = float(res.fe_mean[ia] - res.fe_mean[ib])
    sd = math.sqrt(float(res.fe_sd[ia]) ** 2 + float(res.fe_sd[ib]) ** 2)  # independent-posterior approximation
    return {"or": math.exp(est), "ci_low": math.exp(est - 1.96 * sd), "ci_high": math.exp(est + 1.96 * sd)}


def main():
    admitted, ident = admitted_cases(), identified_pairs()
    e2 = frame_e2(admitted, ident)
    e3 = frame_e3(admitted, ident, e2)
    out, lines = {}, ["# Trial-level regression checks (generated by study/analysis/robustness_mixed.py)", ""]

    f2 = "y ~ C(role, Treatment('implement')) + C(basis, Treatment('P'))"
    g2, m2 = gee(e2, f2), mixed(e2, f2)
    terms2 = {"ordering_vs_implementing": "C(role, Treatment('implement'))[T.order]",
              "knowledge_vs_prompt": "C(basis, Treatment('P'))[T.K]",
              "second_record_vs_prompt": "C(basis, Treatment('P'))[T.R]"}
    lines += [f"## Experiment 2, the agent task: {len(e2):,} trials, {e2['model'].nunique()} models, {e2['case'].nunique()} cases", "",
              "| contrast | GEE odds ratio (95% CI) | P | mixed-effects odds ratio (95% CI) |", "|---|---|---|---|"]
    for key, name in terms2.items():
        if name not in g2.params.index:
            continue
        a, b = term_gee(g2, name), term_mixed(m2, name)
        out[f"e6.gee.{key}"] = a; out[f"e6.mixed.{key}"] = b
        lines.append(f"| {key.replace('_', ' ')} | {a['or']:.2f} ({a['ci_low']:.2f} to {a['ci_high']:.2f}) | {a['p']:.3g} | {b['or']:.2f} ({b['ci_low']:.2f} to {b['ci_high']:.2f}) |")
    out["e6.n.e2"] = {"trials": int(len(e2)), "models": int(e2["model"].nunique()), "cases": int(e2["case"].nunique())}

    f3 = "y ~ C(cond, Treatment('baseline'))"
    g3, m3 = gee(e3, f3), mixed(e3, f3)
    cells = {c: f"C(cond, Treatment('baseline'))[T.{c}]" for c in ("assess", "assess_free", "neutral", "neutral_free")}
    lines += ["", f"## Experiment 3, the assessment before acting, with the matched agent-task cells as baseline: {len(e3):,} trials, {e3['model'].nunique()} models, {e3['case'].nunique()} cases", "",
              "| contrast | GEE odds ratio (95% CI) | P | mixed-effects odds ratio (95% CI) |", "|---|---|---|---|"]
    for c, name in cells.items():
        a, b = term_gee(g3, name), term_mixed(m3, name)
        out[f"e6.gee.{c}_vs_baseline"] = a; out[f"e6.mixed.{c}_vs_baseline"] = b
        lines.append(f"| {c} vs matched baseline | {a['or']:.2f} ({a['ci_low']:.2f} to {a['ci_high']:.2f}) | {a['p']:.3g} | {b['or']:.2f} ({b['ci_low']:.2f} to {b['ci_high']:.2f}) |")
    a, b = contrast_gee(g3, cells["assess"], cells["neutral"]), contrast_mixed(m3, cells["assess"], cells["neutral"])
    out["e6.gee.assess_vs_neutral"] = a; out["e6.mixed.assess_vs_neutral"] = b
    lines.append(f"| assess vs neutral | {a['or']:.2f} ({a['ci_low']:.2f} to {a['ci_high']:.2f}) | {a['p']:.3g} | {b['or']:.2f} ({b['ci_low']:.2f} to {b['ci_high']:.2f}) |")
    out["e6.n.e3"] = {"trials": int(len(e3)), "models": int(e3["model"].nunique()), "cases": int(e3["case"].nunique())}
    out["e6.mixed.variance"] = {"e2": {k: float(v) for k, v in zip(m2.model.vcp_names, np.exp(m2.vcp_mean))},
                                "e3": {k: float(v) for k, v in zip(m3.model.vcp_names, np.exp(m3.vcp_mean))}}
    lines += ["", "Odds ratios above 1 mean more harmful actions than the reference. The GEE clusters trials by model with an exchangeable working correlation and robust standard errors; the mixed-effects model has random intercepts for model and case, fitted by variational Bayes, with intervals from the posterior standard deviations.", ""]
    json.dump(out, open(HERE / "robustness_mixed.json", "w", encoding="utf-8"), indent=1)
    (HERE / "robustness_mixed.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
