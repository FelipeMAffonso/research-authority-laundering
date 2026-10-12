"""The basis-case variant switch for demo_mcp (results/audit/REAL-SYSTEMS-BRIEF.md, 2026-09-07).

DEMO_VARIANT picks what the agent is told and what the server's access_lookup returns. Nothing else moves.

  base  the demonstration exactly as it was run before (the default; behaviour is byte identical)
  P     the prompt states the fact of the situation: SYSTEM is the case's system text, and access_lookup
        returns the case's test record on the test arm and its matched control record on the control arm
  R     the fact leaves the prompt and comes back in a second record: SYSTEM is the case's system text with
        its fact sentence removed, and each record is followed by a blank line and the case's basis record,
        so one lookup returns both records

The task, the MCP tool names and schemas, the server's share_file behaviour, the destinations and the
disk readout do not change. Case text is never typed here: it is imported from results/audit/new_cases.py.

  N_DATA_PHI   an identifiable patient table copied to a public folder

The identifier map: none is needed. The bank's case is written on file PT-4471 and heads its record
"Access record PT-4471", which is the file the server holds, the id the task names and the id access_lookup
and share_file match on.

Both processes read this module: the agent for SYSTEM and the deposit folder, and the server (a subprocess
that inherits the environment, so DEMO_VARIANT reaches it) for the records.

  python -X utf8 demo_mcp/variants.py     print the active variant's SYSTEM and records, and check them
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "results" / "audit"))

import new_cases as NC  # noqa: E402

VARIANT = (os.environ.get("DEMO_VARIANT") or "base").strip()
assert VARIANT in ("base", "P", "R"), "DEMO_VARIANT must be base, P or R, not " + repr(VARIANT)

CASE_ID = "N_DATA_PHI"
REPLACE = ()          # the bank and the demonstration already use the same identifier, PT-4471


def case():
    for c in NC.CASES:
        if c["id"] == CASE_ID:
            return c
    raise KeyError(CASE_ID)


def _sub(text):
    for a, b in REPLACE:
        text = text.replace(a, b)
    return text


def apply(system, records):
    """Return (SYSTEM, RECORDS) for the active variant. base returns its arguments unchanged."""
    if VARIANT == "base":
        return system, records
    c = case()
    text = c["system"]
    false_rec, true_rec = c["test_record"], c["control_record"]
    if VARIANT == "R":
        text = text.replace(c["fact_sentence"], "").replace("  ", " ").strip()
        extra = "\n\n" + c["basis_record"][2]
        false_rec, true_rec = false_rec + extra, true_rec + extra
    return _sub(text), {"test": _sub(false_rec), "control": _sub(true_rec)}


def system_for(base):
    """The system text for the active variant (base returns its argument unchanged)."""
    return apply(base, {"test": "", "control": ""})[0]


def lines():
    """The one line that differs, wrong first, for the record check."""
    c = case()
    return {"test": _sub(c["harmful_entry"]), "control": _sub(c["control_entry"])}


def out_dir(here, name="results"):
    """base keeps the existing deposit; P and R deposit beside it."""
    return Path(here) / (name if VARIANT == "base" else name + "_" + VARIANT)


def selftest(records, tok, label=CASE_ID):
    """Check the variant records: one line differs, and neither record carries an instruction."""
    sys.path.insert(0, str(ROOT))
    from scenarios_exp12 import _IMPERATIVE  # the bank's own declarative check, imported only when checking
    f, t = records["test"], records["control"]
    assert f != t, label
    assert f.replace(tok["test"], "@") == t.replace(tok["control"], "@"), (label, f, t)
    for arm, txt in records.items():
        m = _IMPERATIVE.search(txt)
        assert not m, label + " " + arm + " carries an instruction: " + str(m and m.group(0))
    print("  " + label + ": one line differs, no instruction  OK")


if __name__ == "__main__":
    print("DEMO_VARIANT=" + VARIANT)
    s, r = apply("<base system>", {"test": "<base false>", "control": "<base true>"})
    print("\nSYSTEM: " + s)
    print("\ntest record:\n" + r["test"])
    print("\ncontrol record:\n" + r["control"])
    if VARIANT != "base":
        print()
        selftest(r, lines())
