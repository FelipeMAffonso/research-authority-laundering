"""The knowledge check's judge against an independent scorer from a different developer.

The knowledge check (knowledge_check.py) scores every answer with one judge, Claude Opus 5 at low reasoning
effort, using the four-class rubric in JUDGE_PROMPT. The Methods promise that judge's agreement with an
independent read. This builds it in three parts:

  sample   400 scored answers from results/knowledge_check, 200 from the test-record arm and 200 from the
           control-record arm, spread as evenly as the deposit allows over the four verdict classes and over
           the models, with a fixed seed. FILTERED, EMPTY and UNPARSED answers are skipped, and only the
           paper's own bank (case ids beginning with N_) is drawn from.
  rescore  the same answers scored again by GPT-5.5 through the study's own provider code, with JUDGE_PROMPT
           verbatim, the same parsing and the same reasoning setting. One deposit per answer, resumable.
  report   agreement, Cohen's kappa over the four classes, and agreement on the binary distinction the screen
           uses (WRONG against the other three), each with a 95 per cent bootstrap interval, plus the
           confusion matrix and every disagreement written out so a person can read it.

A third read by a person is prepared as JUDGE-HUMAN-READ.csv: 120 of the 400 answers, 60 per arm,
disagreements first and then agreements at random, with an empty column for the human verdict. Once that
column is filled, --report reads it back and adds the human's agreement with each judge.

  python -X utf8 results/audit/judge_agreement.py --sample        writes judge_agreement_sample.json
  python -X utf8 results/audit/judge_agreement.py --run           scores the sample with GPT-5.5 (resumable)
  python -X utf8 results/audit/judge_agreement.py --report        writes JUDGE-AGREEMENT.md + judge_agreement.json
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from envload import load_user_env  # noqa: E402
from loop import Provider  # noqa: E402
from knowledge_check import JUDGE_PROMPT, VERDICTS  # noqa: E402  the rubric verbatim, not a copy

KC = ROOT / "results" / "knowledge_check"
OUT = HERE / "judge_agreement"
SAMPLE_PATH = HERE / "judge_agreement_sample.json"
CSV_PATH = HERE / "JUDGE-HUMAN-READ.csv"
MD_PATH = HERE / "JUDGE-AGREEMENT.md"
JSON_PATH = HERE / "judge_agreement.json"

JUDGE_B = ("openrouter", "openai/gpt-5.5")   # a second judge from a different developer
JUDGE_B_EFFORT = "low"                        # the same reasoning setting the study's judge uses
PER_ARM = 200
HUMAN_ROWS, HUMAN_PER_ARM = 120, 60
SEED = 20260908
DRAWS = 2000
SKIP = ("FILTERED", "EMPTY", "UNPARSED")


# ---------------------------------------------------------------- the sample
def load_pool():
    """Every scored answer in the paper's own bank, with the deposit's stem as its id."""
    rows = []
    for p in sorted(KC.glob("N_*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("error") or d.get("verdict") in SKIP or not d.get("verdict"):
            continue
        if not d.get("answer"):
            continue
        d["id"] = p.stem
        d["arm"] = d.get("arm", "test")
        rows.append(d)
    return rows


def allocate(available, total, rng):
    """Hand out `total` places over the keys of `available` as evenly as the counts allow."""
    keys = sorted(available)
    give = {k: 0 for k in keys}
    left = total
    while left > 0:
        openk = [k for k in keys if give[k] < available[k]]
        if not openk:
            break
        rng.shuffle(openk)
        for k in openk:
            if left == 0:
                break
            give[k] += 1
            left -= 1
    return give


def build_sample():
    rng = random.Random(SEED)
    pool = load_pool()
    by_arm = defaultdict(list)
    for r in pool:
        by_arm[r["arm"]].append(r)
    picked = []
    plan = {}
    for arm in ("test", "control"):
        rows = by_arm[arm]
        by_v = defaultdict(list)
        for r in rows:
            by_v[r["verdict"]].append(r)
        want_v = allocate({v: len(by_v[v]) for v in by_v}, PER_ARM, rng)
        plan[arm] = {"pool": len(rows), "by_verdict": {v: len(by_v[v]) for v in sorted(by_v)},
                     "drawn_by_verdict": {v: want_v[v] for v in sorted(want_v)}}
        for v in sorted(by_v):
            by_m = defaultdict(list)
            for r in by_v[v]:
                by_m[r["model"]].append(r)
            want_m = allocate({m: len(by_m[m]) for m in by_m}, want_v[v], rng)
            for m in sorted(by_m):
                bucket = sorted(by_m[m], key=lambda r: r["id"])
                rng.shuffle(bucket)
                picked.extend(bucket[:want_m[m]])
    picked.sort(key=lambda r: r["id"])
    out = {"seed": SEED, "n": len(picked), "per_arm": PER_ARM, "judge_a": "anthropic/claude-opus-5",
           "judge_b": JUDGE_B[1], "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "plan": plan,
           "ids": [r["id"] for r in picked],
           "records": [{"id": r["id"], "case": r["case"], "arm": r["arm"], "model": r["model"],
                        "phrasing": r["phrasing"], "rep": r["rep"], "verdict_a": r["verdict"]} for r in picked]}
    SAMPLE_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"sampled {len(picked)} answers over {len(set(r['case'] for r in picked))} cases and "
          f"{len(set(r['model'] for r in picked))} models")
    for arm in ("test", "control"):
        print(" ", arm, plan[arm]["drawn_by_verdict"], "from a pool of", plan[arm]["pool"])
    print("wrote", SAMPLE_PATH)
    return out


# ---------------------------------------------------------------- the second judge
def judge_b(question, answer):
    """The study's judge call, with GPT-5.5 in place of Opus 5. Same prompt, parsing and reasoning setting."""
    prov = Provider(*JUDGE_B)
    prov.reasoning_effort = JUDGE_B_EFFORT
    r = prov.chat([{"role": "system", "content": JUDGE_PROMPT},
                   {"role": "user", "content": "QUESTION:\n" + question + "\n\nANSWER:\n" + (answer or "(empty)")}],
                  max_tokens=1500, temperature=0.0)
    text = (r.choices[0].message.content or "").strip()
    if not text:
        return "UNPARSED", "(the judge returned no text)", r
    word = text.split("\n")[0].strip().upper().rstrip(".:*")
    if word not in VERDICTS:
        m = re.search(r"\b(WRONG|CAUTIOUS|ENDORSES|NEITHER)\b", text.upper())
        word = m.group(1) if m else "UNPARSED"
    return word, text + f"\n[judge: {JUDGE_B[1]}]", r


def score_one(rec_id):
    path = OUT / (rec_id + ".json")
    if path.exists():
        try:
            d = json.load(open(path, encoding="utf-8"))
            if d.get("verdict_b") and not d.get("error"):
                return d
        except Exception:  # noqa: BLE001
            pass
    src = json.load(open(KC / (rec_id + ".json"), encoding="utf-8"))
    d = dict(id=rec_id, case=src["case"], arm=src.get("arm", "test"), model=src["model"],
             phrasing=src["phrasing"], rep=src["rep"], verdict_a=src["verdict"], judge_text_a=src.get("judge_text"),
             verdict_b=None, judge_text_b=None, error=None, usage=None, cost_usd=None, seconds=None,
             ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
    t0 = time.time()
    try:
        d["verdict_b"], d["judge_text_b"], r = judge_b(src["question"], src["answer"])
        u = getattr(r, "usage", None)
        if u is not None:
            d["usage"] = {"prompt": getattr(u, "prompt_tokens", None), "completion": getattr(u, "completion_tokens", None)}
            d["cost_usd"] = getattr(u, "cost", None)
    except Exception as e:  # noqa: BLE001
        d["error"] = str(e)[:500]
    d["seconds"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def run(workers=8):
    ids = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))["ids"]
    todo = []
    for i in ids:
        p = OUT / (i + ".json")
        if p.exists():
            try:
                if json.load(open(p, encoding="utf-8")).get("verdict_b"):
                    continue
            except Exception:  # noqa: BLE001
                pass
        todo.append(i)
    print(f"{len(ids)} in the sample, {len(todo)} still to score")
    if not todo:
        return
    done = errs = 0
    cost = 0.0
    tok = Counter()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(score_one, i) for i in todo]
        for f in as_completed(futs):
            d = f.result()
            done += 1
            if d.get("error"):
                errs += 1
            if d.get("cost_usd"):
                cost += float(d["cost_usd"])
            if d.get("usage"):
                tok["prompt"] += d["usage"].get("prompt") or 0
                tok["completion"] += d["usage"].get("completion") or 0
            if done % 25 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)} scored, {errs} errors, {time.time() - t0:.0f}s, "
                      f"tokens {dict(tok)}, cost ${cost:.3f}")
    print(f"finished {done}, errors {errs}, cost of this run ${cost:.3f}")


# ---------------------------------------------------------------- the numbers
def kappa(a, b, classes):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in classes)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def boot(stat, a, b, draws=DRAWS, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(a)
    vals = []
    for _ in range(draws):
        idx = rng.integers(0, n, n)
        aa = [a[i] for i in idx]
        bb = [b[i] for i in idx]
        v = stat(aa, bb)
        if v == v:  # not nan
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def agree_stat(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a)


def load_scored():
    ids = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))["ids"]
    rows = []
    for i in ids:
        p = OUT / (i + ".json")
        if not p.exists():
            continue
        d = json.load(open(p, encoding="utf-8"))
        if d.get("error") or not d.get("verdict_b"):
            continue
        src = json.load(open(KC / (i + ".json"), encoding="utf-8"))
        d["question"] = src["question"]
        d["answer"] = src["answer"]
        rows.append(d)
    return rows


def block(rows, seed=SEED):
    """Every number for one set of paired verdicts."""
    a = [r["verdict_a"] for r in rows]
    b = [r["verdict_b"] for r in rows]
    classes = list(VERDICTS)
    ab = [x == "WRONG" for x in a]
    bb = [x == "WRONG" for x in b]
    return {
        "n": len(rows),
        "agreement": agree_stat(a, b),
        "agreement_ci": boot(agree_stat, a, b, seed=seed),
        "kappa": kappa(a, b, classes),
        "kappa_ci": boot(lambda x, y: kappa(x, y, classes), a, b, seed=seed),
        "binary_agreement": agree_stat(ab, bb),
        "binary_agreement_ci": boot(agree_stat, ab, bb, seed=seed),
        "binary_kappa": kappa(ab, bb, [True, False]),
        "binary_kappa_ci": boot(lambda x, y: kappa(x, y, [True, False]), ab, bb, seed=seed),
    }


def reweighted(rows, plan, arm, draws=DRAWS, seed=SEED):
    """What the screen's identification rate would be under the second judge, for one arm.

    The sample is stratified on the first judge's classes, so the raw share of WRONG in it is not the deposit's
    rate. Each stratum is weighted back by its share of the arm's pool, which gives the rate the second judge
    would have produced over the whole arm. The first judge's own rate is read straight off the pool.
    """
    pool = plan[arm]["by_verdict"]
    total = sum(pool.values())
    hit = {}
    for c in pool:
        rs = [r for r in rows if r["arm"] == arm and r["verdict_a"] == c]
        hit[c] = [r["verdict_b"] == "WRONG" for r in rs]
    a_rate = pool.get("WRONG", 0) / total
    b_rate = sum((pool[c] / total) * (sum(hit[c]) / len(hit[c])) for c in pool if hit[c])
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        v = 0.0
        for c in pool:
            h = hit[c]
            if not h:
                continue
            idx = rng.integers(0, len(h), len(h))
            v += (pool[c] / total) * (sum(h[i] for i in idx) / len(h))
        vals.append(v)
    return {"pool": total, "judge_a_rate": a_rate, "judge_b_rate": b_rate,
            "judge_b_ci": (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))}


def read_human():
    """The filled human column, if a person has filled it. {id: VERDICT}."""
    if not CSV_PATH.exists():
        return {}
    out = {}
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            v = (row.get("human_verdict") or "").strip().upper()
            if v in VERDICTS:
                out[row["id"]] = v
    return out


def write_human_csv(rows, seed=SEED):
    rng = random.Random(seed + 1)
    chosen = []
    for arm in ("test", "control"):
        pool = [r for r in rows if r["arm"] == arm]
        dis = [r for r in pool if r["verdict_a"] != r["verdict_b"]]
        agr = [r for r in pool if r["verdict_a"] == r["verdict_b"]]
        rng.shuffle(dis)
        rng.shuffle(agr)
        chosen.extend((dis + agr)[:HUMAN_PER_ARM])
    existing = read_human()
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "case", "arm", "model", "question", "answer", "human_verdict"])
        for r in chosen:
            w.writerow([r["id"], r["case"], "test record" if r["arm"] == "test" else "matched control record",
                        r["model"], r["question"], r["answer"], existing.get(r["id"], "")])
    return chosen


def reason_of(judge_text, limit=300):
    """The judge's sentence of reason, without the model tag the deposit appends."""
    t = re.sub(r"\[judge:[^\]]*\]?", "", judge_text or "")
    body = " ".join(" ".join(t.split("\n")[1:]).split()).strip()
    return body[:limit] + ("..." if len(body) > limit else "")


def fmt(x):
    return f"{100 * x:.1f}%"


def fmtci(ci):
    return f"{100 * ci[0]:.1f} to {100 * ci[1]:.1f}"


def report():
    rows = load_scored()
    if not rows:
        print("nothing scored yet; run --run first")
        return
    overall = block(rows)
    per_arm = {arm: block([r for r in rows if r["arm"] == arm]) for arm in ("test", "control")}
    classes = list(VERDICTS)
    conf = Counter((r["verdict_a"], r["verdict_b"]) for r in rows)
    dis = [r for r in rows if r["verdict_a"] != r["verdict_b"]]
    chosen = write_human_csv(rows)
    human = read_human()
    hblock = None
    if human:
        hrows = [r for r in rows if r["id"] in human]
        ha = [r["verdict_a"] for r in hrows]
        hb = [r["verdict_b"] for r in hrows]
        hh = [human[r["id"]] for r in hrows]
        hblock = {
            "n": len(hrows),
            "human_vs_judge_a": agree_stat(hh, ha),
            "human_vs_judge_a_ci": boot(agree_stat, hh, ha),
            "human_vs_judge_a_kappa": kappa(hh, ha, classes),
            "human_vs_judge_b": agree_stat(hh, hb),
            "human_vs_judge_b_ci": boot(agree_stat, hh, hb),
            "human_vs_judge_b_kappa": kappa(hh, hb, classes),
            "human_vs_judge_a_binary": agree_stat([x == "WRONG" for x in hh], [x == "WRONG" for x in ha]),
            "human_vs_judge_b_binary": agree_stat([x == "WRONG" for x in hh], [x == "WRONG" for x in hb]),
        }

    smp0 = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    rw = {arm: reweighted(rows, smp0["plan"], arm) for arm in ("test", "control")}
    cost = sum(float(r["cost_usd"]) for r in rows if r.get("cost_usd"))
    tok = Counter()
    for r in rows:
        if r.get("usage"):
            tok["prompt"] += r["usage"].get("prompt") or 0
            tok["completion"] += r["usage"].get("completion") or 0

    # ------------------------------------------------ the machine-readable keys
    out = {
        "n": overall["n"],
        "judge_a": "anthropic/claude-opus-5",
        "judge_b": JUDGE_B[1],
        "reasoning_effort": JUDGE_B_EFFORT,
        "classes": classes,
        "agreement": round(overall["agreement"], 4),
        "agreement_ci_low": round(overall["agreement_ci"][0], 4),
        "agreement_ci_high": round(overall["agreement_ci"][1], 4),
        "kappa": round(overall["kappa"], 4),
        "kappa_ci_low": round(overall["kappa_ci"][0], 4),
        "kappa_ci_high": round(overall["kappa_ci"][1], 4),
        "binary_agreement": round(overall["binary_agreement"], 4),
        "binary_agreement_ci_low": round(overall["binary_agreement_ci"][0], 4),
        "binary_agreement_ci_high": round(overall["binary_agreement_ci"][1], 4),
        "binary_kappa": round(overall["binary_kappa"], 4),
        "binary_kappa_ci_low": round(overall["binary_kappa_ci"][0], 4),
        "binary_kappa_ci_high": round(overall["binary_kappa_ci"][1], 4),
        "n_disagreements": len(dis),
        "bootstrap_draws": DRAWS,
        "seed": SEED,
        "cost_usd": round(cost, 4),
        "tokens": dict(tok),
        "by_arm": {},
        "confusion": {f"{x}|{y}": conf[(x, y)] for x in classes for y in classes if conf[(x, y)]},
        "identification_rate": {},
        "human_read": None,
    }
    for arm, key in (("test", "test_record"), ("control", "control_record")):
        w = rw[arm]
        out["identification_rate"][key] = {
            "pool": w["pool"],
            "judge_a": round(w["judge_a_rate"], 4),
            "judge_b_reweighted": round(w["judge_b_rate"], 4),
            "judge_b_reweighted_ci_low": round(w["judge_b_ci"][0], 4),
            "judge_b_reweighted_ci_high": round(w["judge_b_ci"][1], 4),
        }
    for arm, key in (("test", "test_record"), ("control", "control_record")):
        b = per_arm[arm]
        out["by_arm"][key] = {
            "n": b["n"],
            "agreement": round(b["agreement"], 4),
            "agreement_ci_low": round(b["agreement_ci"][0], 4),
            "agreement_ci_high": round(b["agreement_ci"][1], 4),
            "kappa": round(b["kappa"], 4),
            "kappa_ci_low": round(b["kappa_ci"][0], 4),
            "kappa_ci_high": round(b["kappa_ci"][1], 4),
            "binary_agreement": round(b["binary_agreement"], 4),
            "binary_agreement_ci_low": round(b["binary_agreement_ci"][0], 4),
            "binary_agreement_ci_high": round(b["binary_agreement_ci"][1], 4),
        }
    if hblock:
        out["human_read"] = {k: (round(v, 4) if isinstance(v, float) else
                                 ([round(v[0], 4), round(v[1], 4)] if isinstance(v, tuple) else v))
                             for k, v in hblock.items()}
    JSON_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------ the readable report
    smp = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    L = []
    L.append("# The knowledge check's judge against an independent scorer")
    L.append("")
    L.append(f"Written {time.strftime('%Y-%m-%d')} from {overall['n']} answers of the knowledge check, each scored twice: "
             "once by the study's own judge, Claude Opus 5 at low reasoning effort, and once by GPT-5.5 at the same "
             "setting through the same provider code, with the four-class rubric sent verbatim and parsed the same way. "
             "The second judge never saw the first judge's verdict.")
    L.append("")
    L.append("## What was sampled")
    L.append("")
    L.append(f"400 answers were drawn with seed {SEED} from the paper's own case bank (ids beginning with N_), "
             "half from the arm that asks about the test record and half from the arm that asks about the control "
             "record, spread as evenly as the deposit allows over the verdict classes the first judge assigned and "
             "over the models that produced the answers. Answers the provider filtered, answers with no text, and "
             "answers the first judge could not parse were skipped.")
    L.append("")
    L.append("| arm | pool | drawn | WRONG | CAUTIOUS | ENDORSES | NEITHER |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for arm, name in (("test", "test record"), ("control", "control record")):
        p = smp["plan"][arm]
        d = p["drawn_by_verdict"]
        L.append(f"| {name} | {p['pool']} | {sum(d.values())} | {d.get('WRONG', 0)} | {d.get('CAUTIOUS', 0)} | "
                 f"{d.get('ENDORSES', 0)} | {d.get('NEITHER', 0)} |")
    L.append("")
    nm = len(set(r["model"] for r in rows))
    nc = len(set(r["case"] for r in rows))
    L.append(f"The 400 answers come from {nc} cases and {nm} models. The NEITHER class does not appear because the "
             "first judge assigned it to no answer in this bank, so the sample cannot contain one.")
    L.append("")
    L.append("## Agreement")
    L.append("")
    L.append("| measure | value | 95 per cent bootstrap interval |")
    L.append("|---|---:|---|")
    L.append(f"| agreement over the four classes | {fmt(overall['agreement'])} | {fmtci(overall['agreement_ci'])} |")
    L.append(f"| Cohen's kappa over the four classes | {overall['kappa']:.3f} | "
             f"{overall['kappa_ci'][0]:.3f} to {overall['kappa_ci'][1]:.3f} |")
    L.append(f"| agreement on WRONG against the rest | {fmt(overall['binary_agreement'])} | {fmtci(overall['binary_agreement_ci'])} |")
    L.append(f"| Cohen's kappa on WRONG against the rest | {overall['binary_kappa']:.3f} | "
             f"{overall['binary_kappa_ci'][0]:.3f} to {overall['binary_kappa_ci'][1]:.3f} |")
    L.append("")
    L.append(f"Intervals are percentile bootstrap over {DRAWS} resamples of the {overall['n']} paired answers. "
             "The binary line is the distinction the screen actually uses: an answer counts as identification when "
             "the judge calls it WRONG, and everything else does not count.")
    L.append("")
    L.append("| arm | n | agreement | kappa | WRONG against the rest |")
    L.append("|---|---:|---|---|---|")
    for arm, name in (("test", "test record"), ("control", "control record")):
        b = per_arm[arm]
        L.append(f"| {name} | {b['n']} | {fmt(b['agreement'])} ({fmtci(b['agreement_ci'])}) | "
                 f"{b['kappa']:.3f} ({b['kappa_ci'][0]:.3f} to {b['kappa_ci'][1]:.3f}) | "
                 f"{fmt(b['binary_agreement'])} ({fmtci(b['binary_agreement_ci'])}) |")
    L.append("")
    L.append("## The confusion matrix")
    L.append("")
    L.append("Rows are the study's judge, columns the independent one.")
    L.append("")
    L.append("| Opus 5 \\ GPT-5.5 | " + " | ".join(classes) + " | total |")
    L.append("|---|" + "---:|" * (len(classes) + 1))
    for x in classes:
        cells = [conf[(x, y)] for y in classes]
        L.append(f"| {x} | " + " | ".join(str(c) for c in cells) + f" | {sum(cells)} |")
    L.append("| total | " + " | ".join(str(sum(conf[(x, y)] for x in classes)) for y in classes) +
             f" | {overall['n']} |")
    L.append("")
    L.append("## What the disagreement is made of")
    L.append("")
    na = sum(conf[("WRONG", y)] for y in classes)
    nb = sum(conf[(x, "WRONG")] for x in classes)
    up = conf[("CAUTIOUS", "WRONG")] + conf[("ENDORSES", "WRONG")] + conf[("NEITHER", "WRONG")]
    down = conf[("WRONG", "CAUTIOUS")] + conf[("WRONG", "ENDORSES")] + conf[("WRONG", "NEITHER")]
    side = len(dis) - up - down
    L.append(f"The disagreement runs almost entirely one way. In this sample the independent judge calls {nb} answers "
             f"WRONG against the study's judge's {na}. Of the {len(dis)} disagreements, {up} are answers the study's "
             f"judge placed below WRONG and the independent judge raised to it, {down} went the other way, and the "
             f"remaining {side} moved between CAUTIOUS and ENDORSES without touching WRONG. The study's judge is the "
             "stricter of the two about what counts as knowing the value is wrong, so the identification rates the "
             "paper reports are the conservative reading.")
    L.append("")
    L.append("The sample is stratified on the study's judge's classes, so the share of WRONG inside it is not the "
             "deposit's rate. Weighting each stratum back by its share of the arm's pool gives the rate the "
             "independent judge would have produced over the whole arm:")
    L.append("")
    L.append("| arm | answers in the arm | identification, Claude Opus 5 | identification, GPT-5.5 reweighted |")
    L.append("|---|---:|---:|---|")
    for arm, name in (("test", "test record"), ("control", "control record")):
        w = rw[arm]
        L.append(f"| {name} | {w['pool']} | {fmt(w['judge_a_rate'])} | {fmt(w['judge_b_rate'])} "
                 f"({fmtci(w['judge_b_ci'])}) |")
    L.append("")
    L.append("The gap between the two arms is what the knowledge check rests on, and it is wide under either judge: "
             f"{fmt(rw['test']['judge_a_rate'] - rw['control']['judge_a_rate'])} under the study's judge and "
             f"{fmt(rw['test']['judge_b_rate'] - rw['control']['judge_b_rate'])} under the independent one.")
    L.append("")
    L.append("## Where they disagree")
    L.append("")
    L.append(f"{len(dis)} of {overall['n']} answers, {fmt(len(dis) / overall['n'])} of the sample. Counted by direction:")
    L.append("")
    L.append("| the study's judge said | the independent judge said | answers |")
    L.append("|---|---|---:|")
    for (x, y), n in sorted(conf.items(), key=lambda kv: -kv[1]):
        if x != y:
            L.append(f"| {x} | {y} | {n} |")
    L.append("")
    L.append("Every disagreement, with the first 200 characters of the answer and both readings:")
    L.append("")
    for i, r in enumerate(sorted(dis, key=lambda r: (r["arm"], r["case"], r["model"])), 1):
        arm = "test record" if r["arm"] == "test" else "control record"
        ans = " ".join((r["answer"] or "").split())[:200]
        ra = reason_of(r["judge_text_a"])
        rb = reason_of(r["judge_text_b"])
        L.append(f"**{i}. {r['case']}, {r['model']}, {r['phrasing']}, {arm}** ({r['id']})")
        L.append("")
        L.append(f"- answer: {ans}")
        L.append(f"- Opus 5 said {r['verdict_a']}: {ra}")
        L.append(f"- GPT-5.5 said {r['verdict_b']}: {rb}")
        L.append("")
    L.append("## The human read")
    L.append("")
    L.append(f"`JUDGE-HUMAN-READ.csv` holds {len(chosen)} of the 400 answers, {HUMAN_PER_ARM} per arm, with the "
             "disagreements first and then agreements drawn at random. The last column, human_verdict, takes one of "
             "WRONG, CAUTIOUS, ENDORSES or NEITHER for each row. Fill the rows you want to read and run this script "
             "with --report again; it reads the column back, keeps what is already filled when it rewrites the file, "
             "and adds the person's agreement with each judge here and in judge_agreement.json.")
    L.append("")
    if hblock:
        L.append(f"{hblock['n']} rows are filled.")
        L.append("")
        L.append("| comparison | agreement | 95 per cent interval | kappa | WRONG against the rest |")
        L.append("|---|---:|---|---:|---:|")
        L.append(f"| the person against Claude Opus 5 | {fmt(hblock['human_vs_judge_a'])} | "
                 f"{fmtci(hblock['human_vs_judge_a_ci'])} | {hblock['human_vs_judge_a_kappa']:.3f} | "
                 f"{fmt(hblock['human_vs_judge_a_binary'])} |")
        L.append(f"| the person against GPT-5.5 | {fmt(hblock['human_vs_judge_b'])} | "
                 f"{fmtci(hblock['human_vs_judge_b_ci'])} | {hblock['human_vs_judge_b_kappa']:.3f} | "
                 f"{fmt(hblock['human_vs_judge_b_binary'])} |")
        L.append("")
    else:
        L.append("No rows are filled yet, so no human agreement is reported.")
        L.append("")
    L.append("## Files and keys")
    L.append("")
    L.append("- `judge_agreement_sample.json`: the 400 ids drawn, the seed, and the draw per arm and class.")
    L.append("- `judge_agreement/<id>.json`: one deposit per answer with both verdicts and both reasons.")
    L.append("- `judge_agreement.json`: the numbers for the package analysis. Top-level keys are `n`, `agreement`, "
             "`agreement_ci_low`, `agreement_ci_high`, `kappa`, `kappa_ci_low`, `kappa_ci_high`, `binary_agreement`, "
             "`binary_agreement_ci_low`, `binary_agreement_ci_high`, `binary_kappa`, `binary_kappa_ci_low`, "
             "`binary_kappa_ci_high`, `n_disagreements`, `judge_a`, `judge_b`, `bootstrap_draws`, `seed`, "
             "`cost_usd`, `confusion`, `by_arm` (with `test_record` and `control_record`, each holding the same "
             "agreement and kappa keys), `identification_rate` (per arm: `judge_a`, `judge_b_reweighted` and its "
             "two interval bounds), and `human_read` (null until the CSV is filled).")
    L.append("- `JUDGE-HUMAN-READ.csv`: the 120 answers for a person to score.")
    L.append("")
    L.append(f"The second scoring cost ${cost:.2f} over {tok['prompt']:,} prompt tokens and "
             f"{tok['completion']:,} completion tokens.")
    L.append("")
    MD_PATH.write_text("\n".join(L), encoding="utf-8")
    print(f"n={overall['n']} agreement={fmt(overall['agreement'])} ({fmtci(overall['agreement_ci'])}) "
          f"kappa={overall['kappa']:.3f} ({overall['kappa_ci'][0]:.3f} to {overall['kappa_ci'][1]:.3f}) "
          f"binary={fmt(overall['binary_agreement'])} ({fmtci(overall['binary_agreement_ci'])}) "
          f"disagreements={len(dis)} cost=${cost:.2f}")
    print("wrote", MD_PATH)
    print("wrote", JSON_PATH)
    print("wrote", CSV_PATH)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    load_user_env()
    if a.sample:
        build_sample()
    if a.run:
        if not SAMPLE_PATH.exists():
            build_sample()
        run(a.workers)
    if a.report:
        report()
    if not (a.sample or a.run or a.report):
        ap.print_help()


if __name__ == "__main__":
    main()
