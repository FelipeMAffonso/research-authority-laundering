"""Shared runner code; the agent task uses its loop, tool and executor code.
"Experiments 1 and 2" and PREREG-EXP12.md below are the earlier numbering and plan of the study, not the paper's.

Runner for Experiments 1 and 2 (PREREG-EXP12.md). Idempotent, cost-capped, randomized order.

  python run_exp12.py --cap 120 --workers 10
  python run_exp12.py --report
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
from scenarios_exp12 import EXP1, EXP2  # noqa: E402

RAW = HERE / "results" / "exp12b_raw"   # v3 declarative bank; exp12_raw is the retained v2 (instruction-form) deposit

# frozen panel: breadth across labs; provider refusals stay in the denominator
PANEL = ["claude-opus-5", "claude-fable-5.1", "claude-sonnet-4.5", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.5",
         "gemini-3.8-flash", "gemini-3.0-flash", "grok-4.6", "deepseek-v4-pro", "qwen3.7-max", "mistral-large",
         "llama-4-maverick"]

REPS = 5


def spent():
    tot = 0.0
    for p in glob.glob(str(RAW / "*.json")):
        try:
            tot += json.load(open(p, encoding="utf-8")).get("cost_usd") or 0.0
        except Exception:  # noqa: BLE001
            pass
    return tot


def build_jobs():
    jobs = []
    for m in PANEL:
        for sid, sc in EXP1.items():          # each case: FALSE (planted) + TRUE-control (true)
            for r in range(REPS):
                jobs.append((m, sc, r, str(RAW), "planted"))
                jobs.append((m, sc, r, str(RAW), "true"))
        for sid, sc in EXP2.items():          # each condition: planted only
            for r in range(REPS):
                jobs.append((m, sc, r, str(RAW), "planted"))
    random.Random(20260905).shuffle(jobs)     # randomized interleaving (frozen seed)
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=float, default=120.0)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        import analyze_exp12
        analyze_exp12.main()
        print(f"\nspent so far: ${spent():.2f}")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    print("env:", load_user_env())
    jobs = build_jobs()
    print(f"exp12: {len(jobs)} trials, {len(PANEL)} models, cap ${a.cap:.0f}, already spent ${spent():.2f}")
    counts = defaultdict(int)
    t0 = time.time()
    stop = {"v": False}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, *j): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                st, _ = f.result()
            except Exception as e:  # noqa: BLE001
                st = "err"; print("EXC", str(e)[:120])
            counts[st] += 1
            if i % 60 == 0:
                sp = spent()
                print(f"  {i}/{len(jobs)} {dict(counts)}  spent ${sp:.2f}  ({(time.time()-t0)/60:.0f}m)")
                if sp >= a.cap and not stop["v"]:
                    stop["v"] = True
                    print(f"!! COST CAP ${a.cap:.0f} reached (${sp:.2f}); cancelling remaining")
                    for ff in futs:
                        ff.cancel()
    print(f"done {dict(counts)}  total spent ${spent():.2f}  ({(time.time()-t0)/60:.0f}m)")


if __name__ == "__main__":
    main()
