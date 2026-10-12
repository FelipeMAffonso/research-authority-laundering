"""The variant switch for demo_drone (the rebuilt study, 2026-09-07).

The demonstration is re-run as a basis case. The engine, the task, the tool names and schemas, the
executor and the scoring are untouched. Only the prompt and the two records change, picked by the
environment variable DEMO_VARIANT:

  base  the demonstration's own prompt and records, byte-identical to the frozen run (the default)
  P     the case's system text, which states the fact of the situation, with the case's two records
  R     the case's system with the fact sentence removed, and each record followed by a blank line and
        the second record that carries the same fact, so the one lookup returns both records

The case text is imported from results/audit/new_cases.py and nothing is typed here. Deposits go to
demo_drone/results_P and results_R; base keeps demo_drone/results.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_ID = "N_PHYS_DRONE"
CASE_PATH = HERE.parent / "results" / "audit" / "new_cases.py"

# Identifier mapping, so the case text carries the identifiers this demonstration's task and world use.
# The bank calls the closed airspace "sector 7"; this demonstration's world, task and route tool call the
# same closed volume "restricted area R-7" and its record "airspace record AR-7", so the case's names are
# replaced by the demonstration's in both the prompt and the records. The heading is rewritten first so
# that it carries the record number the task names.
RENAMES = (("Airspace record, sector 7", "Airspace record AR-7, restricted area R-7"),
           ("Sector 7", "Restricted area R-7"),
           ("sector 7", "restricted area R-7"))


def _bank():
    spec = importlib.util.spec_from_file_location("new_cases_bank", CASE_PATH)
    mod = importlib.util.module_from_spec(spec)
    _bank_dir = str(Path(spec.origin).parent)   # the bank imports sibling packages since 2026-09-08
    if _bank_dir not in sys.path:
        sys.path.append(_bank_dir)
    spec.loader.exec_module(mod)
    return mod.CASES


def case():
    for c in _bank():
        if c["id"] == CASE_ID:
            return c
    raise SystemExit("case " + CASE_ID + " is not in " + str(CASE_PATH))


def variant():
    v = (os.environ.get("DEMO_VARIANT") or "base").strip()
    if v not in ("base", "P", "R"):
        raise SystemExit("DEMO_VARIANT must be base, P or R, not " + repr(v))
    return v


def _ids(text):
    for a, b in RENAMES:
        text = text.replace(a, b)
    return text


def resolve(system, records, tokens, out):
    """Return (variant, SYSTEM, RECORDS, TOKENS, OUT) for the active DEMO_VARIANT.

    TOKENS carries the one line that differs between the two records, which the selftest uses to prove
    the records differ in that line and in nothing else.
    """
    v = variant()
    if v == "base":
        return v, system, dict(records), dict(tokens), out
    c = case()
    sys_text = _ids(c["system"])
    false_rec, true_rec = _ids(c["test_record"]), _ids(c["control_record"])
    toks = {"test": _ids(c["harmful_entry"]), "control": _ids(c["control_entry"])}
    if v == "R":
        sys_text = sys_text.replace(_ids(c["fact_sentence"]), "").replace("  ", " ").strip()
        basis = _ids(c["basis_record"][2])
        false_rec = false_rec + "\n\n" + basis
        true_rec = true_rec + "\n\n" + basis
    return v, sys_text, {"test": false_rec, "control": true_rec}, toks, HERE / ("results_" + v)
