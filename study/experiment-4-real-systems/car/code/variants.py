"""The variant switch for demo_car v2 (the rebuilt study, 2026-09-07).

The demonstration is re-run as a basis case. The engine, the task, the tool names and schemas, the
executor, the scoring and the record gates are untouched. Only the prompt and the two records change,
picked by the environment variable DEMO_VARIANT:

  base  the demonstration's own prompt and records, byte-identical to the frozen v2 run (the default)
  P     the case's system text, which states the fact of the situation, with the case's two records
  R     the case's system with the fact sentence removed, and each record followed by a blank line and
        the second record that carries the same fact, so the one lookup returns both records

The case text is imported from results/audit/new_cases.py and nothing is typed here. Deposits go to
demo_car/results_P and results_R; base keeps demo_car/results_v2. The v1 script demo_car/sim.py is not
wired to this switch: its record pair carried an instruction and v2 replaced it.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_ID = "N_VEH_CROSSING"
CASE_PATH = HERE.parent / "results" / "audit" / "new_cases.py"

# Identifier mapping, so the case text carries the identifier this demonstration's task names. The task
# asks for the maneuver "at the intersection ahead (sensor record CT-1)", so the case's record heading
# gains that record number. Nothing else is renamed: the maneuver words the executor accepts (proceed,
# yield) live in the tool schema, which is unchanged.
RENAMES = (("Crossing record, Elm and 3rd", "Crossing record CT-1, Elm and 3rd"),)


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


def resolve(system, records, clauses, out):
    """Return (variant, SYSTEM, RECORDS, CLAUSES, OUT) for the active DEMO_VARIANT.

    CLAUSES carries the one line that differs between the two records, which check_records uses to prove
    the records differ in that line and in nothing else.
    """
    v = variant()
    if v == "base":
        return v, system, dict(records), dict(clauses), out
    c = case()
    sys_text = _ids(c["system"])
    false_rec, true_rec = _ids(c["test_record"]), _ids(c["control_record"])
    cl = {"test": _ids(c["harmful_entry"]), "control": _ids(c["control_entry"])}
    if v == "R":
        sys_text = sys_text.replace(_ids(c["fact_sentence"]), "").replace("  ", " ").strip()
        basis = _ids(c["basis_record"][2])
        false_rec = false_rec + "\n\n" + basis
        true_rec = true_rec + "\n\n" + basis
    return v, sys_text, {"test": false_rec, "control": true_rec}, cl, HERE / ("results_" + v)
