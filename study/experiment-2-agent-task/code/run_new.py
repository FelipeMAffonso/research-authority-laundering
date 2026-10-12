"""Runner for the agent task of the rebuilt study (scenarios_new.NEW). Idempotent, cost-capped, randomized.

  python run_new.py --smoke                      one trial (one model, one case) to prove the loop runs
  python run_new.py --pilot 60 --cap 5           a random sample, to confirm the per-trial cost
  python run_new.py --cap 400 --workers 8        everything not yet deposited
  python run_new.py --roles implement --basis P R --cases N_PHYS_FEEDER N_MED_KCL   subsets

Deposit: results/new_raw/<model>__<scenario>__<test|control>__t<rep>.json, one file per trial. The test arm
runs the case's test record and the control arm its matched control record.
"""
import argparse
import glob
import json
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from envload import load_user_env  # noqa: E402
from worlds import run_one  # noqa: E402
from scenarios_new import NEW, selftest  # noqa: E402
from run_exp12 import PANEL as PANEL13, REPS  # noqa: E402

# 2026-09-07: all models everywhere. The 13 of the task families plus the three the matched experiment added.
PANEL = PANEL13 + ["gpt-6-astra", "claude-opus-4.8", "claude-haiku-4.5"]
RAW = HERE / "results" / "new_raw"


def spent():
    tot = 0.0
    for p in glob.glob(str(RAW / "*.json")):
        try:
            tot += json.load(open(p, encoding="utf-8")).get("cost_usd") or 0.0
        except Exception:  # noqa: BLE001
            pass
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=400.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--true-reps", type=int, default=REPS, dest="true_reps")
    ap.add_argument("--roles", nargs="+", default=["implement", "order"])
    ap.add_argument("--basis", nargs="+", default=["K", "P", "R"])
    ap.add_argument("--cases", nargs="+", default=None)
    ap.add_argument("--models", nargs="+", default=PANEL)
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--elicit", choices=["exclude", "only", "include"], default="exclude",
                    help="Condition E scenarios (ids ending __E): excluded by default, run alone with 'only'")
    ap.add_argument("--mech", choices=["exclude", "only", "include"], default="exclude",
                    help="Condition M scenarios (ids ending __M_<cell>): excluded by default, run alone with 'only'")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    print("selftest:", selftest())
    print("env:", load_user_env())

    def wanted(sc):
        if sc["role"] not in a.roles or sc["basis"] not in a.basis or (a.cases is not None and sc["case"] not in a.cases):
            return False
        if sc.get("mech"):
            return a.mech != "exclude"
        if sc.get("elicit"):
            return a.elicit != "exclude" and a.mech != "only"
        return a.elicit != "only" and a.mech != "only"
    scs = [sc for sc in NEW.values() if wanted(sc)]
    jobs = [(m, sc, r, str(RAW), v) for m in a.models for sc in scs
            for v in ("test", "control") for r in range(a.reps if v == "test" else a.true_reps)]
    random.Random(20260907).shuffle(jobs)
    jobs.sort(key=lambda j: j[4] != "test")  # stable: the test-record arm first, then the control arm
    if a.smoke:
        jobs = [j for j in jobs if j[4] == "test"][:1]
    elif a.pilot:
        jobs = jobs[:a.pilot]
    print(f"new: {len(scs)} scenarios, {len(jobs)} trials, {len(a.models)} models, cap ${a.cap:.0f}, already spent ${spent():.2f}")
    counts = defaultdict(int)
    t0 = time.time()
    stop = {"v": False}
    own = 0.0  # this run's own spending; the cap applies to it, not to the folder (2026-09-08: several runs share the folder,
    # and the elicitation run cancelled 5,500 jobs because the folder total already exceeded its cap)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, *j): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                st, path = f.result()
            except Exception as e:  # noqa: BLE001
                st, path = "err", ""
                print("EXC", type(e).__name__, str(e)[:160])
            counts[st] += 1
            if st == "ok" and path:
                try:
                    own += json.load(open(path, encoding="utf-8")).get("cost_usd") or 0.0
                except Exception:  # noqa: BLE001
                    pass
            if a.smoke and path:
                d = json.load(open(path, encoding="utf-8"))
                print(json.dumps({k: d.get(k) for k in ("model", "scenario", "outcome", "acted_on_harmful_entry", "completed_legit_task",
                                                         "entry_delivered", "action_calls", "cost_usd", "error")}, indent=1)[:1500])
                print("FINAL TEXT:", (d.get("final_text") or "")[:600])
            if i % 60 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} {dict(counts)}  this run ${own:.2f}, folder ${spent():.2f}  ({(time.time() - t0) / 60:.0f}m)", flush=True)
                if own >= a.cap and not stop["v"]:
                    stop["v"] = True
                    print(f"!! COST CAP ${a.cap:.0f} reached by this run; cancelling remaining", flush=True)
                    for ff in futs:
                        ff.cancel()
    print(f"done {dict(counts)}  this run ${own:.2f}, folder ${spent():.2f}  ({(time.time() - t0) / 60:.0f}m)", flush=True)


if __name__ == "__main__":
    main()
