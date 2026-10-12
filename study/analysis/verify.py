"""Rerun the analysis and check the manuscript against it, number by number.

    python -X utf8 study/analysis/verify.py                 recompute, then check the draft
    python -X utf8 study/analysis/verify.py --no-run        check against the PAPER-NUMBERS.json already on disk
    python -X utf8 study/analysis/verify.py --manuscript PATH
    python -X utf8 study/analysis/verify.py --list          print every key the analysis produces

It runs `analyze.py`, which rebuilds every table and rewrites `PAPER-NUMBERS.json` from the package data, and
then reads the manuscript and compares every number that carries a key. It exits non-zero and names every
mismatch. Until the manuscript carries keys it says so and exits zero.

THE CONVENTION
--------------
A number in the manuscript carries its key in an HTML comment placed immediately after it, on the same line:

    commission reached 18 per cent <!-- num:e2.commission.all.model_weighted --> among those pairs

The key names an entry in PAPER-NUMBERS.json. By default the entry's `value` is compared, which for a rate is
the per cent with every model weighted equally. To check another part of the same entry, add the field after a
hash:

    2,386 of 13,228 trials <!-- num:e2.commission.all.model_weighted#denominator -->
    interval 11 to 26 <!-- num:e2.commission.all.model_weighted#interval -->

The fields are `value` (the default), `pooled`, `numerator`, `denominator`, `models` and `interval`. A line may
carry several markers; each one is matched against the numbers written since the previous marker on that line.
An `interval` marker takes the last two numbers written; every other field takes the last one.

Numbers may be written with thousands separators, a per cent sign, or a minus sign. The comparison is made at
the precision the manuscript uses: a manuscript that writes 18 passes against 17.6041, one that writes 17.6
passes against 17.6041 and fails against 17.5. Counts must match exactly.

A key the manuscript names that the analysis does not produce is a failure, not a skip.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parent
NUMBERS_FILE = HERE / "PAPER-NUMBERS.json"
# The manuscript checked when --manuscript is not given.
MANUSCRIPTS = [STUDY / "paper" / "DRAFT-main.md"]

MARKER = re.compile(r"<!--\s*num:([A-Za-z0-9_.\-]+)(?:#([A-Za-z_]+))?\s*-->")
NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
FIELDS = ("value", "pooled", "numerator", "denominator", "models", "interval", "p", "cases", "draws")


def find_manuscript(given: str | None) -> Path | None:
    if given:
        p = Path(given)
        return p if p.exists() else None
    for p in MANUSCRIPTS:
        if p.exists():
            return p
    return None


def parse_number(token: str) -> float:
    return float(token.replace(",", ""))


def decimals(token: str) -> int:
    return len(token.split(".")[1]) if "." in token else 0


def same(written: str, computed) -> bool:
    """The manuscript's number against the computed one, at the precision the manuscript writes."""
    if computed is None:
        return False
    d = decimals(written)
    return round(parse_number(written), d) == round(float(computed), d)


def markers_in(text: str):
    """(line number, key, field, the number tokens written for it) for every marker in the manuscript."""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        cut = 0
        for m in MARKER.finditer(line):
            segment = line[cut:m.start()]
            cut = m.end()
            key, field = m.group(1), (m.group(2) or "value")
            tokens = NUMBER.findall(segment)
            out.append((lineno, key, field, tokens, line.strip()))
    return out


def compare(text: str, numbers: dict) -> tuple[list[str], int, int]:
    """(the mismatches, how many markers were found, how many numbers were compared)."""
    found = markers_in(text)
    failures = []
    checked = 0
    for lineno, key, field, tokens, line in found:
        where = f"line {lineno}, key {key}" + (f"#{field}" if field != "value" else "")
        if key not in numbers:
            failures.append(f"{where}: the analysis produces no such key")
            continue
        if field not in FIELDS:
            failures.append(f"{where}: unknown field, use one of {', '.join(FIELDS)}")
            continue
        computed = numbers[key].get(field)
        if field == "interval":
            if not isinstance(computed, list):
                failures.append(f"{where}: the analysis has no interval for this key")
                continue
            if len(tokens) < 2:
                failures.append(f"{where}: an interval marker needs two numbers before it, found {tokens or 'none'}")
                continue
            lo, hi = tokens[-2], tokens[-1]
            checked += 1
            if not (same(lo, computed[0]) and same(hi, computed[1])):
                failures.append(f"{where}: the manuscript says {lo} to {hi}, the analysis says "
                                f"{computed[0]:.4f} to {computed[1]:.4f}   ({line})")
            continue
        if not tokens:
            failures.append(f"{where}: no number written before the marker   ({line})")
            continue
        written = tokens[-1]
        checked += 1
        if field == "p":
            # "P < 0.001" passes when the computed P is below 0.001; any other P is compared at the
            # precision written, so "P = 0.012" must match 0.012
            segment = line[:line.find("<!--")] if "<!--" in line else line
            if "< " + written in segment.replace("<", "< ").replace("  ", " ") or f"<{written}" in segment:
                if computed is None or float(computed) >= parse_number(written):
                    failures.append(f"{where}: the manuscript says P < {written}, the analysis says {computed}   ({line})")
                continue
            if not same(written, computed):
                failures.append(f"{where}: the manuscript says P = {written}, the analysis says {computed}   ({line})")
            continue
        if not same(written, computed):
            failures.append(f"{where}: the manuscript says {written}, the analysis says {computed}   ({line})")
    return failures, len(found), checked


def selftest(numbers: dict) -> int:
    """An injected fault beside a clean control, on a real number, so the convention itself is proved to refuse.
    It uses whichever key the analysis produced first, so it keeps working as the keys change."""
    key = next(k for k in sorted(numbers)
               if k != "meta" and isinstance(numbers[k].get("value"), (int, float))
               and numbers[k].get("numerator") is not None)
    entry = numbers[key]
    value, num, den = entry["value"], entry["numerator"], entry["denominator"]
    clean = (f"the rate was {value:.4f} per cent <!-- num:{key} -->, that is {num} <!-- num:{key}#numerator --> "
             f"of {den} <!-- num:{key}#denominator -->.")
    faulty = (f"the rate was {value + 5:.4f} per cent <!-- num:{key} -->, that is {num + 1} "
              f"<!-- num:{key}#numerator --> of {den} <!-- num:{key}#denominator -->.")
    missing = f"a number marked with no key the analysis has: 5 <!-- num:{key}.no.such.thing -->."
    ok = True
    f1, n1, c1 = compare(clean, numbers)
    if f1 or c1 != 3:
        ok = False
        print(f"  FAIL the clean control did not pass: {f1}")
    f2, _, _ = compare(faulty, numbers)
    if len(f2) != 2:
        ok = False
        print(f"  FAIL the injected faults were not both caught: {f2}")
    f3, _, _ = compare(missing, numbers)
    if len(f3) != 1:
        ok = False
        print(f"  FAIL an unknown key was not reported: {f3}")
    print(("selftest PASS" if ok else "selftest FAIL") + f" on key {key}: a clean control passes, "
          "a changed value and a changed numerator are both caught, an unknown key is reported.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-run", action="store_true", help="do not rerun analyze.py first")
    ap.add_argument("--manuscript", help="path to the manuscript to check")
    ap.add_argument("--list", action="store_true", help="print every key the analysis produces and stop")
    ap.add_argument("--selftest", action="store_true", help="prove the checker refuses a wrong number, then stop")
    a = ap.parse_args()
    if a.selftest:
        a.no_run = True

    if not a.no_run:
        sys.path.insert(0, str(HERE))
        import analyze
        analyze.main()

    if not NUMBERS_FILE.exists():
        print(f"no numbers file at {NUMBERS_FILE}; run analyze.py")
        return 2
    numbers = json.load(open(NUMBERS_FILE, encoding="utf-8"))

    if a.selftest:
        return selftest(numbers)

    if a.list:
        for key in sorted(k for k in numbers if k != "meta"):
            n = numbers[key]
            print(f"{key}\t{n.get('value')}\t{n.get('what')}")
        return 0

    manuscript = find_manuscript(a.manuscript)
    if manuscript is None:
        print("no manuscript found at " + " or ".join(str(p) for p in MANUSCRIPTS))
        return 2
    text = manuscript.read_text(encoding="utf-8")
    failures, found, checked = compare(text, numbers)
    if not found:
        print(f"no marked numbers in the manuscript yet ({manuscript}).")
        print(f"The analysis produced {len(numbers) - 1:,} numbers; add a marker beside a number to have it checked, "
              "for example: 18 per cent <!-- num:e2.commission.all.model_weighted -->")
        return 0

    print(f"manuscript: {manuscript}")
    print(f"marked numbers found: {found}; compared: {checked}; mismatches: {len(failures)}")
    for f in failures:
        print("  MISMATCH " + f)
    if failures:
        return 1
    print("every marked number in the manuscript matches the analysis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
