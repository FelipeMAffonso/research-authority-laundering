"""The DEMO_VARIANT switch for the telescope demonstration (the rebuilt study, 2026-09-07).

The environment variable DEMO_VARIANT selects the prompt and the records:

  base  (default) the demonstration exactly as it ran, record only. Behaviour is unchanged.
  P     the prompt states the fact of the situation and the record contradicts it. SYSTEM is the case's
        system text; the records are the case's test and matched control records.
  R     the fact is taken out of the prompt and comes back in a second record beside the case record, so
        one lookup returns both.

Everything comes from results/audit/new_cases.py, case N_VEH_TELESCOPE, by import. The only text written
here is the identifier map below, which swaps the bank's slot name, target name, clock time and geometry
for the ones this demonstration's task, catalogue and engine already use, so that the prompt, the record
and the engine readout all describe the same world. Only SYSTEM, RECORDS and TOKENS change: the task, the
tool names, the tool schemas, the executor, the scoring, the flags and the hash-manifest step do not.

The deposit goes to demo_telescope/results_P or demo_telescope/results_R; base keeps results/.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CASE_ID = "N_VEH_TELESCOPE"

_spec = importlib.util.spec_from_file_location("new_cases_bank",
                                               str(ROOT / "results" / "audit" / "new_cases.py"))
_bank = importlib.util.module_from_spec(_spec)
_bank_dir = str(Path(_spec.origin).parent)   # the bank imports sibling packages since 2026-09-08
if _bank_dir not in sys.path:
    sys.path.append(_bank_dir)
_spec.loader.exec_module(_bank)
CASE = next(c for c in _bank.CASES if c["id"] == CASE_ID)

# The bank's identifiers and numbers, mapped onto this demonstration's own. Applied in this order to the
# system text, to both records and to the second record.
ID_MAP = [
    # the record heading: the task asks for Sun-avoidance record SA-41 for slot S-3, and the engine only
    # accepts slot S-3 (sim.SLOT)
    ("Sun-safety record, slot S-14", "Sun-safety record SA-41, slot S-3"),
    ("Ephemeris, today 14:00, Cerro Paranal", "Ephemeris, 2026-06-15 21:30 UTC, Cerro Paranal"),
    # the slot's real clock time: sim.SLOT_UTC is 2026-06-15 21:30:00 UTC, 20 minutes long
    ("The requested slot is 14:00 today", "The requested slot is S-3, 2026-06-15 21:30 UTC"),
    ("Slot: today 14:00 to 14:20", "Slot: 2026-06-15 21:30 to 21:50 UTC"),
    # the target: the engine executes catalogue names only, and the task names CAL-17 (sim.NEAR_SUN)
    ("HD 12345", "CAL-17"),
    # the real geometry at that slot, as astropy computes it in the selftest: CAL-17 sits 6.000 degrees
    # from the Sun and the Sun is 5.368 degrees above the horizon at Cerro Paranal
    ("the target is within 6 degrees of it", "the target is 6.0 degrees from it"),
    ("5.8 degrees", "6.0 degrees"),
    ("Sun altitude: 52 degrees", "Sun altitude: 5.4 degrees"),
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
    # the mapping has to have landed: no bank identifier may survive into what the agent reads
    for text in [system] + list(records.values()):
        for stale in ("S-14", "HD 12345", "14:00", "5.8 degrees", "52 degrees"):
            assert stale not in text, "identifier map missed " + stale
    if VARIANT == "R":
        assert CASE["fact_sentence"].split(",")[0] not in system, "the fact sentence is still in the prompt"
    return system, records, tokens


if __name__ == "__main__":
    print("DEMO_VARIANT =", VARIANT, " deposit:", RESULTS_DIRNAME)
    if VARIANT != "base":
        s, r, t = build()
        print("\nSYSTEM:\n" + s)
        print("\nTEST RECORD:\n" + r["test"])
        print("\nCONTROL RECORD:\n" + r["control"])
        print("\nTOKENS:", t)
