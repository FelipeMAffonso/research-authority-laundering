"""The DEMO_VARIANT switch for the Opentrons OT-2 demonstration (the rebuilt study, 2026-09-07).

The environment variable DEMO_VARIANT selects the prompt and the records:

  base  (default) the demonstration exactly as it ran, record only. Behaviour is unchanged.
  P     the prompt states the fact of the situation and the record contradicts it. SYSTEM is the case's
        system text; the records are the case's test and matched control records.
  R     the fact is taken out of the prompt and comes back in a second record beside the case record, so
        one lookup returns both.

Everything comes from results/audit/new_cases.py, case N_LAB_COLUMN, by import. The only text written here
is the identifier map below, which swaps the bank's plate name and record heading for the ones this
demonstration's task already uses. The occupied column (1) and the empty column (7) are the same in the
bank and in the demonstration, so the scoring is untouched. Only SYSTEM and RECORDS change: the task, the
tool names, the tool schemas, the executor, the scoring and the flags do not.

The deposit goes to demo_lab_ot2/results_P or demo_lab_ot2/results_R; base keeps results/.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CASE_ID = "N_LAB_COLUMN"

_spec = importlib.util.spec_from_file_location("new_cases_bank",
                                               str(ROOT / "results" / "audit" / "new_cases.py"))
_bank = importlib.util.module_from_spec(_spec)
_bank_dir = str(Path(_spec.origin).parent)   # the bank imports sibling packages since 2026-09-08
if _bank_dir not in sys.path:
    sys.path.append(_bank_dir)
_spec.loader.exec_module(_bank)
CASE = next(c for c in _bank.CASES if c["id"] == CASE_ID)

# The bank's identifiers, mapped onto this demonstration's own. Applied in this order to the system text,
# to both records and to the second record.
ID_MAP = [
    # the record heading: the task asks for plate record PR-9 on plate P-9 (sim.TASK)
    ("Layout record, plate P-4", "Layout record PR-9, plate P-9"),
    ("P-4", "P-9"),
]

VARIANT = (os.environ.get("DEMO_VARIANT") or "base").strip() or "base"
if VARIANT not in ("base", "P", "R"):
    raise SystemExit("DEMO_VARIANT must be base, P or R, not " + repr(VARIANT))

RESULTS_DIRNAME = "results" if VARIANT == "base" else "results_" + VARIANT
SUFFIX = "" if VARIANT == "base" else "-" + VARIANT


def _map(text):
    for old, new in ID_MAP:
        text = text.replace(old, new)
    return text


def build():
    """Return (SYSTEM, RECORDS, TOKENS) for the active variant. Only called when VARIANT is P or R."""
    system = _map(CASE["system"])
    false_rec, true_rec = _map(CASE["test_record"]), _map(CASE["control_record"])
    if VARIANT == "R":
        system = system.replace(_map(CASE["fact_sentence"]), "").replace("  ", " ").strip()
        extra = "\n\n" + _map(CASE["basis_record"][2])
        false_rec, true_rec = false_rec + extra, true_rec + extra
    records = {"test": false_rec, "control": true_rec}
    tokens = {"test": _map(CASE["harmful_entry"]), "control": _map(CASE["control_entry"])}
    for text in [system] + list(records.values()):
        assert "P-4" not in text, "identifier map missed P-4"
    if VARIANT == "R":
        assert "column 1 holds the last remaining patient samples" not in system, \
            "the fact sentence is still in the prompt"
    return system, records, tokens


def check(records, tokens):
    """The one-line difference and the declarative check, the one the other demonstrations run in their
    selftest. This demonstration has no selftest of its own, so it is here."""
    f, t = records["test"], records["control"]
    assert f != t, "records are identical"
    assert f.replace(tokens["test"], "@") == t.replace(tokens["control"], "@"), \
        "records differ in more than one line"
    for arm, txt in records.items():
        low = txt.lower()
        for word in (" must ", " do ", " proceed", " run ", " should ", " please "):
            assert word not in low, arm + " record carries imperative language: " + word
    return True


if __name__ == "__main__":
    print("DEMO_VARIANT =", VARIANT, " deposit:", RESULTS_DIRNAME)
    if VARIANT != "base":
        s, r, t = build()
        check(r, t)
        print("\nSYSTEM:\n" + s)
        print("\nTEST RECORD:\n" + r["test"])
        print("\nCONTROL RECORD:\n" + r["control"])
        print("\nTOKENS:", t)
        print("\nrecords differ in one line only and carry no instruction  OK")
