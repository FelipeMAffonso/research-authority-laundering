"""Prompt (P) and second-record (R) placements for the local job service."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "results" / "audit"))
import new_cases

CASE = next(item for item in new_cases.CASES if item["id"] == "N_OFF_ALPHAFOLD_JOBS")


def selected(value=None):
    variant = value or os.environ.get("DEMO_VARIANT", "P")
    if variant not in ("P", "R"):
        raise ValueError("DEMO_VARIANT must be P or R")
    return variant


def apply(variant=None):
    variant = selected(variant)
    system = CASE["system"]
    records = {"test": CASE["test_record"], "control": CASE["control_record"]}
    if variant == "R":
        system = system.replace(CASE["fact_sentence"], "").replace("  ", " ").strip()
        records = {arm: text + "\n\n" + CASE["basis_record"][2] for arm, text in records.items()}
    return system, records


def out_dir(here, variant=None):
    return Path(here) / ("results_" + selected(variant))


def selftest():
    sys.path.insert(0, str(ROOT))
    from scenarios_exp12 import _IMPERATIVE
    for variant in ("P", "R"):
        system, records = apply(variant)
        assert (CASE["fact_sentence"] in system) == (variant == "P")
        assert records["test"].replace(CASE["harmful_entry"], "@") == records["control"].replace(CASE["control_entry"], "@")
        assert sum(left != right for left, right in zip(records["test"].splitlines(), records["control"].splitlines())) == 1
        for text in records.values():
            assert not _IMPERATIVE.search(text), text
            assert (CASE["basis_record"][2] in text) == (variant == "R")
    try:
        selected("base")
    except ValueError:
        pass
    else:
        raise AssertionError("base variant accepted")
    print("P/R: one declarative line differs; basis placement and no-base check OK")


if __name__ == "__main__":
    selftest()
    system, records = apply()
    print("DEMO_VARIANT=" + selected())
    print(system)
    for arm, text in records.items():
        print(arm + "\n" + text)
