"""The basis-case variant switch for demo_canvas (results/audit/EXTENSIONS-BRIEF.md, 2026-09-08).

DEMO_VARIANT picks what the agent is told and what the lookup returns. Nothing else moves. There is no base
variant for the office systems: they were built as basis cases from the start.

  P  the prompt states the fact of the situation: SYSTEM is the case's system text plus the study's
     implementing-role sentence, and the lookup returns the case's test record on the test arm and its
     matched control record on the control arm
  R  the fact leaves the prompt and comes back in a second record: SYSTEM is the case's system text with its
     fact sentence removed, and each record is followed by a blank line and the case's basis record, so one
     lookup returns both records

Case text is never typed here: it is imported from results/audit/new_cases.py by id, and the role sentence
from scenarios_new.ROLE_SENTENCE, so the demonstration's prompt is the study's prompt word for word.

  python -X utf8 demo_canvas/variants.py         print the active variant's SYSTEM and records and check them
  python -X utf8 demo_canvas/variants.py --both  do that for P and R
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "results" / "audit"))

import new_cases as NC  # noqa: E402
from scenarios_new import ROLE_SENTENCE  # noqa: E402
from scenarios_exp12 import _IMPERATIVE  # noqa: E402  the bank's own declarative check

CASE_ID = "N_OFF_CANVAS_GRADES"
VARIANT = (os.environ.get("DEMO_VARIANT") or "P").strip()


def set_variant(v):
    """Set the variant for this process (the --variant flag); the environment variable is the default."""
    global VARIANT
    v = (v or "P").strip()
    assert v in ("P", "R"), "variant must be P or R, not " + repr(v)
    VARIANT = v
    os.environ["DEMO_VARIANT"] = v
    return VARIANT


def case():
    for c in NC.CASES:
        if c["id"] == CASE_ID:
            return c
    raise KeyError(CASE_ID)


def system_text(variant=None):
    """The case's system text for the variant, plus the study's implementing-role sentence."""
    v = variant or VARIANT
    c = case()
    text = c["system"]
    if v == "R":
        text = text.replace(c["fact_sentence"], "").replace("  ", " ").strip()
    return text.rstrip() + ROLE_SENTENCE["implement"]


def records(variant=None):
    """{"test": the test record, "control": the control record} for the variant."""
    v = variant or VARIANT
    c = case()
    f, t = c["test_record"], c["control_record"]
    if v == "R":
        extra = "\n\n" + c["basis_record"][2]
        f, t = f + extra, t + extra
    return {"test": f, "control": t}


def tokens():
    c = case()
    return {"test": c["harmful_entry"], "control": c["control_entry"]}


def lookup(variant=None):
    """(name, description) of the lookup tool; the R variant says the related records come with it."""
    v = variant or VARIANT
    name, desc = case()["lookup"]
    if v == "R":
        desc = desc.rstrip(".") + ", together with the related records on file."
    return name, desc


def task():
    return case()["request"]


def out_dir(here, name="results"):
    return Path(here) / (name + "_" + VARIANT)


def check_records(variant=None):
    """Refuse a variant whose records differ in more than the one line, or carry an instruction."""
    v = variant or VARIANT
    r, tok = records(v), tokens()
    f, t = r["test"], r["control"]
    assert f != t, v + ": the records are identical"
    assert f.replace(tok["test"], "@") == t.replace(tok["control"], "@"), (v, f, t)
    for arm, txt in r.items():
        m = _IMPERATIVE.search(txt)
        assert not m, v + " " + arm + " record carries an instruction: " + str(m and m.group(0))
    return True


def show(variant=None):
    v = variant or VARIANT
    c = case()
    print("=== DEMO_VARIANT=" + v + "  case " + c["id"] + " ===")
    print("SYSTEM: " + system_text(v))
    print("TASK: " + task())
    print("LOOKUP: " + str(lookup(v)))
    r = records(v)
    print("\ntest record:\n" + r["test"])
    print("\ncontrol record:\n" + r["control"])
    check_records(v)
    print("\n  one line differs, no instruction  OK")


if __name__ == "__main__":
    if "--both" in sys.argv:
        for v in ("P", "R"):
            show(v)
            print()
    else:
        show()
