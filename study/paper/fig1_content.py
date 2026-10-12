"""Everything Figure 1 shows, read out of the package at build time.

Nothing here is typed by hand: the case text comes from `study/cases/cases.json`, the quoted answers from
`study/experiment-1-knowledge-check/data`, the tool calls and the receiving systems' readouts from
`study/experiment-4-real-systems/*/data` or, for a case that runs only in the lookup-and-act loop, from
`study/experiment-2-agent-task/data`. Every number comes from `study/analysis/PAPER-NUMBERS.json`.

The module refuses, with a non-zero exit, when a case, a model, a quotable sentence or a committed trial
cannot be found, so a stale figure can never be built from a memory of the data.

Both `build_fig1.py` (which renders the figure) and `figures.py` (which writes the caption) read this, so
the figure and its caption cannot drift apart.
"""
from __future__ import annotations

import glob
import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
E1 = STUDY / "experiment-1-knowledge-check"
E2 = STUDY / "experiment-2-agent-task"
E4 = STUDY / "experiment-4-real-systems"
NUMBERS_FILE = STUDY / "analysis" / "PAPER-NUMBERS.json"

# the three cases the figure walks through, in the order they are drawn
FIG1_CASES = ["N_PHYS_FEEDER", "N_EVD_RENT", "N_OFF_CALENDAR"]

# a short name for each case, for the card footers
CASE_LABELS = {
    "N_PHYS_FEEDER": "the hospital feeder",
    "N_EVD_RENT": "the rent transfer",
    "N_OFF_CALENDAR": "the doctoral defence",
}

MODEL_NAMES = {
    "claude-fable-5.1": "Claude Fable 5.1",
    "claude-haiku-4.5": "Claude Haiku 4.5",
    "claude-opus-4.8": "Claude Opus 4.8",
    "claude-opus-5": "Claude Opus 5",
    "claude-sonnet-4.5": "Claude Sonnet 4.5",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "gemini-3.0-flash": "Gemini 3.0 Flash",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gpt-5.5": "GPT-5.5",
    "gpt-5.6-luna": "GPT-5.6 Luna",
    "gpt-5.6-sol": "GPT-5.6 Sol",
    "gpt-6-astra": "GPT-6 Astra",
    "grok-4.6": "Grok 4.6",
    "llama-4-maverick": "Llama 4 Maverick",
    "mistral-large": "Mistral Large",
    "qwen3.7-max": "Qwen 3.7 Max",
}

SCORED = ("WRONG", "CAUTIOUS", "ENDORSES", "NEITHER")
# a sentence that plainly objects to the recorded value carries one of these
NEGATION_CUES = ("do not ", "don't ", "should not ", "must not ", "never ", "stop ", "do NOT ")
QUOTE_MIN, QUOTE_MAX = 25, 200


def die(msg: str):
    sys.exit(f"fig1_content: {msg}")


def numbers() -> dict:
    if not NUMBERS_FILE.exists():
        die(f"the register is not on disk: {NUMBERS_FILE}")
    return json.loads(NUMBERS_FILE.read_text(encoding="utf-8"))


def num(reg: dict, key: str, field: str = "value"):
    if key not in reg:
        die(f"the register has no key {key}")
    if field not in reg[key] or reg[key][field] is None:
        die(f"the register entry {key} has no {field}")
    return reg[key][field]


def cases() -> dict:
    path = STUDY / "cases" / "cases.json"
    if not path.exists():
        die(f"the case bank is not on disk: {path}")
    by_id = {c["id"]: c for c in json.loads(path.read_text(encoding="utf-8"))}
    for cid in FIG1_CASES:
        if cid not in by_id:
            die(f"the bank has no case {cid}")
    return by_id


# --------------------------------------------------------------------------- the knowledge check


def identified_pairs() -> set[tuple[str, str]]:
    """(case, model) where the model called the value wrong in a majority of its scored answers."""
    tally = defaultdict(lambda: [0, 0])
    for p in sorted((E1 / "data").glob("*.jsonl.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("case") not in FIG1_CASES or r.get("arm") != "test":
                    continue
                if r.get("verdict") not in SCORED:
                    continue
                cell = tally[(r["case"], r["model"])]
                cell[1] += 1
                cell[0] += r["verdict"] == "WRONG"
    return {k for k, v in tally.items() if v[1] and v[0] * 2 > v[1]}


def asked_sentence(case_id: str, model: str, required: bool = True) -> str | None:
    """The model's own shortest complete sentence, from an answer the judge scored WRONG, that plainly
    objects to the recorded value. One rule for every case, so no sentence is hand-picked."""
    path = E1 / "data" / f"{model}.jsonl.gz"
    if not path.exists():
        die(f"no knowledge-check answers for {model}")
    found = set()
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("case") != case_id or r.get("arm") != "test" or r.get("verdict") != "WRONG":
                continue
            for raw in (r.get("answer") or "").split("\n"):
                s = re.sub(r"[*_`#]", "", raw).strip().lstrip("-").strip()
                s = re.sub(r"^\d+[.)]\s*", "", s).strip()
                if not (QUOTE_MIN <= len(s) <= QUOTE_MAX) or not s.endswith("."):
                    continue
                low = s.lower()
                if any(cue.lower() in low for cue in NEGATION_CUES):
                    found.add(s)
    if not found:
        if required:
            die(f"no answer of {model} on {case_id} gives one quotable sentence objecting to the value")
        return None
    return sorted(found, key=lambda s: (len(s), s))[0]


# --------------------------------------------------------------------------- the acting half


def e4_system_of(case_id: str) -> str | None:
    """Which real system, if any, runs this case, read from Experiment 4's own tables. Not every system's
    deposit carries the case id in its rows, so the results file is the mapping."""
    path = E4 / "results.md"
    if not path.exists():
        die(f"the real-systems results file is not on disk: {path}")
    header, rows = None, []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            if header is None:
                header = cells
            elif set("".join(cells)) <= set("-: "):
                continue
            elif len(cells) == len(header):
                rows.append(dict(zip(header, cells)))
        else:
            header = None
    for r in rows:
        if "system" not in r or "case" not in r:
            continue
        found = re.findall(r"\bN_[A-Z0-9_]+\b", r["case"])
        if found and found[0] == case_id:
            folder = r["system"].split(",")[0].strip()
            if (E4 / folder / "data" / "P").is_dir():
                return folder
    return None


HARM_FLAGS = ("hospital_left_unserved", "doctoral_defence_cancelled", "harmful",
              "acted_on_harmful_entry", "committed_harm")


def _harmful(row: dict) -> bool:
    return any(bool(row.get(f)) for f in HARM_FLAGS if f in row)


def _readout(row: dict, system: str) -> str:
    """The receiving system's own words about its own state. Every system writes one; the field is either
    at the top level or inside that system's own block."""
    if isinstance(row.get("system_readout"), str) and row["system_readout"].strip():
        return row["system_readout"].strip()
    block = row.get(system)
    if isinstance(block, dict) and isinstance(block.get("readout"), str) and block["readout"].strip():
        return block["readout"].strip()
    for value in row.values():
        if isinstance(value, dict) and isinstance(value.get("readout"), str) and value["readout"].strip():
            return value["readout"].strip()
    die(f"the {system} deposit carries no readout to quote")


def _fmt_call(tool: str, args: dict) -> str:
    inside = ", ".join(f'{k}="{v}"' for k, v in args.items())
    return f"{tool}({inside})"


def _tool_steps(row: dict) -> list[dict]:
    """The tool calls a real-systems trial recorded. Systems write them either as `action_calls` with a
    `tool` key or as a `trace` with a `name` key, so both shapes are read."""
    out = []
    for block in (row.get("action_calls"), row.get("trace")):
        for c in block or []:
            if not isinstance(c, dict) or not isinstance(c.get("args"), dict):
                continue
            name = c.get("tool") or c.get("name")
            if name:
                out.append({"tool": name, "args": c["args"]})
        if out:
            break
    return out


def e4_committed(case_id: str, system: str, model: str) -> dict | None:
    path = E4 / system / "data" / "P" / f"{model}.jsonl.gz"
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("arm") != "test" or not _harmful(r):
                continue
            steps = _tool_steps(r)
            if not steps:
                continue
            act = steps[-1]
            return {"call": _fmt_call(act["tool"], act["args"]),
                    "readout": _readout(r, system),
                    "engine": (r.get("engine") or "").strip(),
                    "from_system": True}
    return None


def e2_committed(case_id: str, model: str) -> dict | None:
    path = E2 / "data" / f"{model}.jsonl.gz"
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if not str(r.get("scenario", "")).startswith(case_id) or not r.get("acted_on_harmful_entry"):
                continue
            calls = r.get("action_calls") or []
            if not calls:
                continue
            c = dict(calls[-1])
            tool = c.pop("tool")
            return {"call": _fmt_call(tool, c),
                    "readout": (r.get("final_text") or "").strip(),
                    "engine": "",
                    "from_system": False}
    return None


def commission_counts(case_id: str, system: str | None) -> dict[str, int]:
    """How many wrong-record trials each model committed on this case."""
    counts: dict[str, int] = {}
    if system:
        for p in sorted((E4 / system / "data" / "P").glob("*.jsonl.gz")):
            model = p.name.replace(".jsonl.gz", "")
            k = 0
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    if r.get("arm") == "test" and _harmful(r):
                        k += 1
            if k:
                counts[model] = k
        return counts
    for p in sorted((E2 / "data").glob("*.jsonl.gz")):
        model = p.name.replace(".jsonl.gz", "")
        k = 0
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if str(r.get("scenario", "")).startswith(case_id) and r.get("acted_on_harmful_entry"):
                    k += 1
        if k:
            counts[model] = k
    return counts


# --------------------------------------------------------------------------- the three cards


def build() -> dict:
    reg = numbers()
    bank = cases()
    ident = identified_pairs()

    cards = []
    used: set[str] = set()
    for cid in FIG1_CASES:
        case = bank[cid]
        system = e4_system_of(cid)
        counts = commission_counts(cid, system)
        eligible = {m: k for m, k in counts.items() if (cid, m) in ident}
        if not eligible:
            die(f"no model both called {cid} wrong when asked and committed the action when acting")
        # walk the models that committed most often on this case, ties broken by name, and take the first
        # that also leaves one quotable sentence and one tool call, so no card is hand-picked
        model = asked = acting = None
        for candidate in sorted(eligible, key=lambda m: (-eligible[m], m)):
            if candidate in used:      # one model per card, so the figure shows three developers
                continue
            sentence = asked_sentence(cid, candidate, required=False)
            if sentence is None:
                continue
            trial = e4_committed(cid, system, candidate) if system else e2_committed(cid, candidate)
            if trial is None:
                continue
            model, asked, acting = candidate, sentence, trial
            break
        if model is None:
            die(f"no unused model on {cid} leaves both a quotable answer and a committed tool call")
        used.add(model)

        cards.append({
            "case": cid,
            "case_label": CASE_LABELS.get(cid, cid),
            "model": model,
            "model_name": MODEL_NAMES.get(model, model),
            "request": case["request"],
            "harmful_entry": case["harmful_entry"],
            "control_entry": case["control_entry"],
            "lookup_tool": case["lookup"][0],
            "action_tool": case["action"][0],
            "asked": asked,
            "call": acting["call"],
            "readout": acting["readout"],
            "engine": acting["engine"],
            "from_system": acting["from_system"],
            "system": system or "",
            "committed_trials": eligible[model],
        })

    return {
        "cards": cards,
        "identification": num(reg, "e1.identification.all_cases"),
        "commission": num(reg, "e2.commission.all.model_weighted"),
        "commission_newest": num(reg, "e2.commission.newest.model_weighted"),
        "commission_faster": num(reg, "e2.commission.faster.model_weighted"),
        "commission_assess": num(reg, "e3.assess.commission"),
        "models": num(reg, "e2.commission.all.model_weighted", "models"),
        "cases_total": num(reg, "e1.cases.total"),
        "cases_admitted": num(reg, "e1.cases.admitted"),
        "agent_trials": num(reg, "e2.invalid_trials", "denominator"),
    }


if __name__ == "__main__":
    data = build()
    for c in data["cards"]:
        print(f"{c['case']:16s} {c['model_name']:18s} committed {c['committed_trials']}x "
              f"| system: {c['system'] or 'the loop'}")
        print(f"   asked   : {c['asked']}")
        print(f"   call    : {c['call']}")
        print(f"   readout : {c['readout'][:110]}")
    print({k: v for k, v in data.items() if k != "cards"})
