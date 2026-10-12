"""The basis-case variant switch for demo_share (results/audit/EXTENSIONS-BRIEF.md, 2026-09-08).

The case is N_OFF_MAIL_RECIPIENT in results/audit/new_cases.py, and no case text is ever typed here: it is
imported by id. There is no base variant for the office systems, so DEMO_VARIANT is P or R (sim.py also takes
--variant, which sets the same thing).

  P  the prompt states the fact of the situation: the system text is the case's, and the lookup returns the
     case's test record on the test arm and its matched control record on the control arm
  R  the fact leaves the prompt and comes back in a second record: the case's fact sentence is removed from the
     system text, and each record is followed by a blank line and the case's basis record, so one lookup
     returns both records

The system text always ends with the study's implementing-role sentence (scenarios_new.ROLE_SENTENCE), which is
what the demonstration is: the action tool is the act itself and nothing checks it afterwards.

  python -X utf8 demo_share/variants.py            print the active variant's prompt and records
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "results" / "audit"))

import new_cases as NC  # noqa: E402
from scenarios_new import ROLE_SENTENCE, _IMPERATIVE  # noqa: E402

CASE_ID = "N_OFF_SHARE"
VARIANTS = ("P", "R")


def case():
    for c in NC.CASES:
        if c["id"] == CASE_ID:
            return c
    raise KeyError(CASE_ID)


def variant_from_env(default="P"):
    v = (os.environ.get("DEMO_VARIANT") or default).strip()
    assert v in VARIANTS, "DEMO_VARIANT must be P or R, not " + repr(v)
    return v


def build(variant):
    """Return the prompt, the two records and the lookup for one variant. Nothing else in the demonstration moves."""
    assert variant in VARIANTS, variant
    c = case()
    system, lookup_name, lookup_desc = c["system"], c["lookup"][0], c["lookup"][1]
    false_rec, true_rec = c["test_record"], c["control_record"]
    if variant == "R":
        system = system.replace(c["fact_sentence"], "").replace("  ", " ").strip()
        lookup_desc = lookup_desc.rstrip(".") + ", together with the related records on file."
        extra = "\n\n" + c["basis_record"][2]
        false_rec, true_rec = false_rec + extra, true_rec + extra
    system = system.rstrip() + ROLE_SENTENCE["implement"]
    return {"case": c, "variant": variant, "system": system, "task": c["request"],
            "lookup_name": lookup_name, "lookup_desc": lookup_desc,
            "records": {"test": false_rec, "control": true_rec},
            "tok": {"test": c["harmful_entry"], "control": c["control_entry"]}}


def out_dir(variant):
    return HERE / ("results_" + variant)


def check(spec):
    """The bank's own declarative check on the records this variant actually sends."""
    f, t = spec["records"]["test"], spec["records"]["control"]
    assert f != t, "records are identical"
    assert f.replace(spec["tok"]["test"], "@") == t.replace(spec["tok"]["control"], "@"), (f, t)
    for arm, txt in spec["records"].items():
        m = _IMPERATIVE.search(txt)
        assert not m, arm + " record carries an instruction: " + str(m and m.group(0))
    assert spec["case"]["fact_sentence"] in spec["system"] if spec["variant"] == "P" else True
    assert spec["case"]["fact_sentence"] not in spec["system"] if spec["variant"] == "R" else True
    return True


if __name__ == "__main__":
    v = sys.argv[1] if len(sys.argv) > 1 else variant_from_env()
    s = build(v)
    print("variant " + v + "   case " + CASE_ID)
    print("\nSYSTEM:\n" + s["system"])
    print("\nTASK:\n" + s["task"])
    print("\nLOOKUP: " + s["lookup_name"] + " -- " + s["lookup_desc"])
    print("\ntest record:\n" + s["records"]["test"])
    print("\ncontrol record:\n" + s["records"]["control"])
    print("\ngate:", check(s))
