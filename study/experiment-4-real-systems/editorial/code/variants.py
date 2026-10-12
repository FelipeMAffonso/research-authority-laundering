"""The basis-case variant switch for demo_editorial (results/audit/EXTENSIONS-BRIEF.md, 2026-09-08).

DEMO_VARIANT picks what the agent is told and what the lookup returns. Nothing else moves. The office and
research software systems have no base variant: they were built as basis cases from the start.

  P  the prompt states the fact of the situation: SYSTEM is the case's system text, and the lookup returns the
     case's test record on the test arm and its matched control record on the control arm
  R  the fact leaves the prompt and comes back in a second record: SYSTEM is the case's system text with its
     fact sentence removed, and each record is followed by a blank line and the case's basis record, so one
     lookup returns both records. The lookup's description gains ", together with the related records on file."
     exactly as scenarios_new.build_case does for the R basis, so the tool still describes what it returns.

Case text is never typed here: it is imported from results/audit/new_cases.py by id.

  N_OFF_EDITORIAL_DECISION   the decision letter for manuscript M-2077

  python -X utf8 demo_editorial/variants.py     print the active variant's SYSTEM and both records, and check them
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "results" / "audit"))

import new_cases as NC  # noqa: E402

CASE_ID = "N_OFF_EDITORIAL_DECISION"
VARIANT = (os.environ.get("DEMO_VARIANT") or "P").strip()
assert VARIANT in ("P", "R"), "DEMO_VARIANT must be P or R, not " + repr(VARIANT)


def set_variant(v):
    """The runner's --variant flag: set it before anything reads VARIANT."""
    global VARIANT
    assert v in ("P", "R"), v
    os.environ["DEMO_VARIANT"] = v
    VARIANT = v


def case():
    for c in NC.CASES:
        if c["id"] == CASE_ID:
            return c
    raise KeyError(CASE_ID)


def system_text():
    c = case()
    if VARIANT == "R":
        return c["system"].replace(c["fact_sentence"], "").replace("  ", " ").strip()
    return c["system"]


def records():
    """{"test": the test record, "control": the control record} for the active variant."""
    c = case()
    f, t = c["test_record"], c["control_record"]
    if VARIANT == "R":
        extra = "\n\n" + c["basis_record"][2]
        f, t = f + extra, t + extra
    return {"test": f, "control": t}


def lookup_desc():
    c = case()
    d = c["lookup"][1]
    if VARIANT == "R":
        return d.rstrip(".") + ", together with the related records on file."
    return d


def tokens():
    c = case()
    return {"test": c["harmful_entry"], "control": c["control_entry"]}


def out_dir(here, name="results"):
    return Path(here) / (name + "_" + VARIANT)


def check_records():
    """One line differs between the two records, and neither carries an instruction."""
    sys.path.insert(0, str(ROOT))
    from scenarios_exp12 import _IMPERATIVE  # the bank's own declarative check
    r, tok = records(), tokens()
    f, t = r["test"], r["control"]
    assert f != t, "records are identical"
    assert f.replace(tok["test"], "@") == t.replace(tok["control"], "@"), (f, t)
    for arm, txt in r.items():
        m = _IMPERATIVE.search(txt)
        assert not m, arm + " record carries an instruction: " + str(m and m.group(0))
    return True


if __name__ == "__main__":
    print("DEMO_VARIANT=" + VARIANT + "   case " + CASE_ID)
    print("\nSYSTEM: " + system_text())
    print("\nLOOKUP: " + case()["lookup"][0] + " - " + lookup_desc())
    r = records()
    print("\ntest record:\n" + r["test"])
    print("\ncontrol record:\n" + r["control"])
    print("\nrecords check:", check_records())
