"""The DEMO_VARIANT switch for the coding-agent shell demonstration (the rebuilt study, 2026-09-07).

The environment variable DEMO_VARIANT selects the prompt and the records:

  base  (default) the demonstration exactly as it ran, record only. Behaviour is unchanged.
  P     the prompt states the fact of the situation and the record contradicts it. SYSTEM is the case's
        system text; the records are the case's test and matched control records.
  R     the fact is taken out of the prompt and comes back in a second record beside the case record, so
        one read of records/AR-31.txt returns both. The second record here is a listing of cold_storage/,
        which this agent can also produce for itself with List or ls, so the R variant also writes that
        listing into records/ beside AR-31.txt (EXTRA_RECORD below).

Everything comes from results/audit/new_cases.py, case N_OPS_ONLYCOPY, by import. The bank's identifiers
already match this demonstration (folder RD-31, backup record AR-31, 200 result files, an empty cold
storage, a file reader, a folder lister and a shell), so there is no identifier mapping at all.

Only SYSTEM and RECORDS change, plus the one extra file in records/ under R. The task, the tool names, the
tool schemas, the guard, the executor, the scoring, the flags and the hash-manifest step do not change.

The deposit goes to demo_shell/results_P or demo_shell/results_R; base keeps results/.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CASE_ID = "N_OPS_ONLYCOPY"

_spec = importlib.util.spec_from_file_location("new_cases_bank",
                                               str(ROOT / "results" / "audit" / "new_cases.py"))
_bank = importlib.util.module_from_spec(_spec)
_bank_dir = str(Path(_spec.origin).parent)   # the bank imports sibling packages since 2026-09-08
if _bank_dir not in sys.path:
    sys.path.append(_bank_dir)
_spec.loader.exec_module(_bank)
CASE = next(c for c in _bank.CASES if c["id"] == CASE_ID)

# no identifier mapping: the bank wrote this case for this demonstration's world
ID_MAP = []

VARIANT = (os.environ.get("DEMO_VARIANT") or "base").strip() or "base"
if VARIANT not in ("base", "P", "R"):
    raise SystemExit("DEMO_VARIANT must be base, P or R, not " + repr(VARIANT))

RESULTS_DIRNAME = "results" if VARIANT == "base" else "results_" + VARIANT
SUFFIX = "" if VARIANT == "base" else "-" + VARIANT

# under R only: the second record is also on disk beside the archive record, because it is a listing the
# agent could produce itself. Path relative to the trial sandbox root, and its text.
EXTRA_RECORD = (("records/cold-storage-listing.txt", CASE["basis_record"][2] + "\n")
                if VARIANT == "R" else None)


def _map(text):
    for old, new in ID_MAP:
        text = text.replace(old, new)
    return text


def build():
    """Return (SYSTEM, RECORDS, TOK) for the active variant. Only called when VARIANT is P or R."""
    system = _map(CASE["system"])
    false_rec, true_rec = _map(CASE["test_record"]), _map(CASE["control_record"])
    if VARIANT == "R":
        system = system.replace(_map(CASE["fact_sentence"]), "").replace("  ", " ").strip()
        extra = "\n\n" + _map(CASE["basis_record"][2])
        false_rec, true_rec = false_rec + extra, true_rec + extra
    records = {"test": false_rec, "control": true_rec}
    tok = {"test": _map(CASE["harmful_entry"]), "control": _map(CASE["control_entry"])}
    if VARIANT == "R":
        assert "only copy" not in system, "the fact sentence is still in the prompt"
    return system, records, tok


if __name__ == "__main__":
    print("DEMO_VARIANT =", VARIANT, " deposit:", RESULTS_DIRNAME, " extra record:", EXTRA_RECORD)
    if VARIANT != "base":
        s, r, t = build()
        print("\nSYSTEM:\n" + s)
        print("\nTEST RECORD:\n" + r["test"])
        print("\nCONTROL RECORD:\n" + r["control"])
        print("\nTOK:", t)
