"""The basis-case variant switch for demo_cloud (results/audit/REAL-SYSTEMS-BRIEF.md, 2026-09-07).

DEMO_VARIANT picks what the agent is told and what the lookup returns. Nothing else moves.

  base  the demonstration exactly as it was run before (the default; behaviour is byte identical)
  P     the prompt states the fact of the situation: SYSTEM is the case's system text, and the lookup
        returns the case's test record on the test arm and its matched control record on the control arm
  R     the fact leaves the prompt and comes back in a second record: SYSTEM is the case's system text with
        its fact sentence removed, and each record is followed by a blank line and the case's basis record,
        so one lookup returns both records

The task, the tool names, the tool schemas, the executor, the scoring, the flags and the hash-manifest step do not
change. Case text is never typed here: it is imported from results/audit/new_cases.py by id.

  C1_firewall  N_SEC_PORT     the production database opened to the whole internet
  C2_bucket    N_SEC_BUCKET   a bucket under a legal hold emptied and deleted

The identifier map (rule 2 of the brief: the demonstration's identifiers win, and the bank is never edited).

  C1_firewall  the bank heads the record "Exposure record, db-prod-1"; the demonstration's task asks for
               "exposure record ER-31", so the heading becomes "Exposure record ER-31, db-prod-1".
  C2_bucket    the bank's bucket is "prod-customer-exports"; the emulator builds, and every tool names,
               "prod-customer-records", so the bucket name is replaced throughout. The bank heads the record
               "Retention record, bucket ..."; the task asks for "decommission record DR-7", so the heading
               becomes "Retention record DR-7, bucket ...".

  python -X utf8 demo_cloud/variants.py     print the active variant's SYSTEM and records, and check them
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

CASE_ID = {"C1_firewall": "N_SEC_PORT", "C2_bucket": "N_SEC_BUCKET"}

# ordered: the bucket rename first, then the heading, so the heading rule sees the renamed bucket
REPLACE = {
    "C1_firewall": (("Exposure record, db-prod-1", "Exposure record ER-31, db-prod-1"),),
    "C2_bucket": (("prod-customer-exports", "prod-customer-records"),
                  ("Retention record, bucket prod-customer-records",
                   "Retention record DR-7, bucket prod-customer-records")),
}


def case(case_key):
    cid = CASE_ID[case_key]
    for c in NC.CASES:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def _sub(text, case_key):
    for a, b in REPLACE.get(case_key, ()):
        text = text.replace(a, b)
    return text


def apply(case_key, system, records, tok):
    """Return (SYSTEM, RECORDS, TOK) for the active variant. base returns its arguments unchanged."""
    if VARIANT == "base":
        return system, records, tok
    c = case(case_key)
    text = c["system"]
    false_rec, true_rec = c["test_record"], c["control_record"]
    if VARIANT == "R":
        text = text.replace(c["fact_sentence"], "").replace("  ", " ").strip()
        extra = "\n\n" + c["basis_record"][2]
        false_rec, true_rec = false_rec + extra, true_rec + extra
    return (_sub(text, case_key),
            {"test": _sub(false_rec, case_key), "control": _sub(true_rec, case_key)},
            {"test": _sub(c["harmful_entry"], case_key), "control": _sub(c["control_entry"], case_key)})


def out_dir(here, name="results"):
    """base keeps the existing deposit; P and R deposit beside it."""
    return Path(here) / (name if VARIANT == "base" else name + "_" + VARIANT)


def manifest_name(name):
    """MANIFEST-CLOUD.json for base, MANIFEST-CLOUD-P.json and MANIFEST-CLOUD-R.json for the variants."""
    if VARIANT == "base":
        return name
    stem, _, ext = name.rpartition(".")
    return stem + "-" + VARIANT + "." + ext


def selftest(pairs):
    """Check every variant record: one line differs, and neither record carries an instruction."""
    sys.path.insert(0, str(ROOT))
    from scenarios_exp12 import _IMPERATIVE  # the bank's own declarative check, imported only when checking
    for label, records, tok in pairs:
        f, t = records["test"], records["control"]
        assert f != t, label
        assert f.replace(tok["test"], "@") == t.replace(tok["control"], "@"), (label, f, t)
        for arm, txt in records.items():
            m = _IMPERATIVE.search(txt)
            assert not m, label + " " + arm + " carries an instruction: " + str(m and m.group(0))
        print("  " + label + ": one line differs, no instruction  OK")


if __name__ == "__main__":
    print("DEMO_VARIANT=" + VARIANT)
    pairs = []
    for key in ("C1_firewall", "C2_bucket"):
        c = case(key)
        s, r, tok = apply(key, "<base system>", {"test": "<base false>", "control": "<base true>"},
                          {"test": "<base>", "control": "<base>"})
        print("\n=== " + key + "  (" + c["id"] + ") ===")
        print("SYSTEM: " + s)
        print("\ntest record:\n" + r["test"])
        print("\ncontrol record:\n" + r["control"])
        pairs.append((key, r, tok))
    if VARIANT != "base":
        print()
        selftest(pairs)
