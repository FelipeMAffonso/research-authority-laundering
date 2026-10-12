"""Verbatim same-trial assessment excerpts and recorded action-tool arguments."""
from __future__ import annotations

import csv
import gzip
import json

from build_common import Evidence, STUDY, esc, read_literal, render_html

EXPERIMENT = STUDY / "experiment-3-assessment-before-acting"
SELECTION = [
    ("gemini-3.0-flash__N_PHYS_FEEDER__implement__P__M_assess__planted__t0", "Hospital feeder", "unsafe and incorrect", None),
    ("gpt-5.6-luna__N_EVD_RENT__implement__P__M_assess__planted__t1", "Rent transfer", "not safe and correct", None),
    ("deepseek-v4-pro__N_OFF_CALENDAR__implement__P__M_assess__planted__t1", "Doctoral defence", "not safe and correct", None),
    ("llama-4-maverick__N_LAB_ACID__implement__K__M_assess__planted__t0", "Laboratory dilution", "incorrect and potentially hazardous", "\n["),
    ("gemini-3.8-flash__N_SEC_TLS__implement__K__M_assess__planted__t1", "Payments service", "neither safe nor correct", None),
    ("gpt-5.6-sol__N_OFF_FORGE_BRANCH__implement__P__M_assess__planted__t1", "Release branch", "not safe or correct", None),
]

CSS = """
* { box-sizing:border-box; }
html,body { margin:0; background:#FAF8F2; }
article { width:1020px; padding:32px 35px 25px; font-family:Arial,Helvetica,sans-serif; color:#272721; }
h1 { font-size:29px; margin:0 0 20px; line-height:1.17; letter-spacing:-.3px; }
.prompt { background:#E8E5DD; padding:15px 19px; margin-bottom:24px; }
.label { font-size:15px; color:#78766F; margin-bottom:8px; }
.prompt p { font-size:19px; line-height:1.4; margin:0; }
.cards { display:grid; grid-template-columns:1fr 1fr; gap:24px 28px; }
.card { border-top:1px solid #D6D2C8; padding-top:14px; display:flex; flex-direction:column; }
.head { display:flex; align-items:center; gap:10px; margin-bottom:11px; }
.letter { font-size:20px; font-weight:700; }
.robot { width:24px; height:27px; }
h2 { font-size:21px; margin:0; }
.case { color:#78766F; font-size:15px; margin:0 0 12px 42px; }
blockquote { font-family:'Courier New',monospace; color:#5B54D6; font-size:17px; line-height:1.37; margin:0 0 15px; white-space:pre-wrap; }
blockquote strong { font-weight:700; }
.call { border-left:2px solid #D6D2C8; padding:8px 11px; background:#EEEAE1; margin-top:auto; }
.call .label { margin:0 0 5px; font-size:13px; }
.call code { font-family:'Courier New',monospace; color:#66645D; font-size:15px; line-height:1.35; overflow-wrap:anywhere; }
footer { margin-top:22px; padding-top:12px; border-top:1px solid #D6D2C8; color:#78766F; font-size:14px; line-height:1.4; }
"""

ROBOT = '<svg class="robot" viewBox="0 0 24 27" aria-hidden="true"><g fill="none" stroke="#78766F" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="7" width="18" height="17" rx="3"/><path d="M12 2V7M8 12V15M16 12V15M8 20H16"/></g></svg>'


def get_trial(model, key):
    path = EXPERIMENT / f"data/{model}.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            # the deposit name is the key the same-trial register uses, and it is the working file's own name
            row_key = row.get("_file") or f"{row['model']}__{row['scenario']}__{row['variant']}__t{row['rep']}"
            row_key = row_key[:-5] if row_key.endswith(".json") else row_key
            if row_key == key:
                return path, line_number, row
    raise ValueError(f"No original trial for {key}")


def build():
    evidence = Evidence("ExtData-same-trial-quotes", "Images 9, 13, 16, 19, 21, 35 and 40: robot, verbatim quotation, emphasized phrase, grey prompt")
    sheet = EXPERIMENT / "SAME-TRIAL-HUMAN-READ.csv"
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        rows = {row["key"]: row for row in csv.DictReader(stream)}
    names_path = STUDY / "paper/figures.py"
    names = read_literal(names_path, "MODEL_NAMES")
    evidence.source(names_path, "MODEL_NAMES literal only")
    prompt_path = EXPERIMENT / "code/scenarios_new.py"
    sentences = read_literal(prompt_path, "MECH_SENTENCES")
    prompt = sentences["assess"].strip()
    sent_prompts = STUDY / "cases/PROMPTS-AS-SENT.md"
    if prompt not in sent_prompts.read_text(encoding="utf-8"):
        raise ValueError("Assessment sentence absent from prompts-as-sent deposit")
    evidence.source(prompt_path, "MECH_SENTENCES.assess", quote=prompt)
    evidence.source(sent_prompts, "exact assessment sentence as sent", quote=prompt)
    cards = []
    for index, (key, label, highlight, stop) in enumerate(SELECTION):
        csv_row = rows[key]
        if csv_row["class as scored"] != "said wrong, committed":
            raise ValueError(f"Wrong CSV class for {key}")
        deposit_path = EXPERIMENT / "same_trial" / f"{key}.json"
        deposit = json.loads(deposit_path.read_text(encoding="utf-8"))
        if deposit["cell"] != "assess" or deposit["verdict"] != "WRONG" or not deposit["committed_harmful_value"]:
            raise ValueError(f"Wrong deposit class for {key}")
        statement = deposit["statement"]
        if statement != csv_row["statement before the tool call"]:
            raise ValueError(f"CSV and deposit disagree for {key}")
        excerpt = statement.split(stop, 1)[0].rstrip() if stop else statement
        if highlight not in excerpt or excerpt not in statement or "\u2014" in excerpt:
            raise ValueError(f"Unquotable excerpt for {key}")
        original_path, line_number, original = get_trial(deposit["model"], key)
        if not original["acted_on_harmful_entry"] or original.get("invalid") or original.get("error"):
            raise ValueError(f"Original trial is not a valid commission for {key}")
        actions = original["action_calls"]
        csv_calls = "; ".join(f"{action.get('tool')}={action.get('value')}" for action in actions)
        if csv_calls != csv_row["action calls (tool, value)"]:
            raise ValueError(f"Action mismatch for {key}")
        case = evidence.case(deposit["case"])
        call_strings = []
        for action in actions:
            if action["tool"] != case["action"][0]:
                raise ValueError(f"Unexpected tool for {key}")
            parameters = ", ".join(f"{field}={json.dumps(value,ensure_ascii=False)}" for field,value in action.items() if field != "tool")
            call_strings.append(action["tool"] + "(" + parameters + ")")
        evidence.source(sheet, key, csv_row=csv_row["n"], classification=csv_row["class as scored"])
        evidence.source(deposit_path, "statement", quote=excerpt, span=[0,len(excerpt)], highlight=highlight,
                        truncated=bool(stop), original_statement=statement)
        evidence.source(original_path, f"JSONL line {line_number}", key=key, action_calls=actions,
                        format="Original tool and every recorded argument, rendered as tool(key=value); no value rewritten")
        rendered = esc(excerpt).replace(esc(highlight), '<strong>'+esc(highlight)+'</strong>', 1)
        if stop:
            rendered += " […]"
        cards.append(f'<section class="card"><div class="head"><span class="letter">{"abcdef"[index]}</span>{ROBOT}<h2>{esc(names[deposit["model"]])}</h2></div>'
                     f'<div class="case">{esc(label)} · {esc(case["family"])}</div><blockquote>{rendered}</blockquote>'
                     f'<div class="call"><div class="label">Then called the action tool</div><code>{esc("; ".join(call_strings))}</code></div></section>')
    wrong_key = "e3.same_trial.assess.said_unsafe_committed"
    total_key = "e3.same_trial.assess.commission"
    wrong = evidence.number(wrong_key, "numerator")
    total = evidence.number(total_key, "numerator")
    document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Statements and subsequent calls</title><style>{CSS}</style></head><body><article>'
    document += f'<h1>Statements followed by a wrong-value tool call</h1><div class="prompt"><div class="label">Assessment sentence as sent, identical for every card</div><p>{esc(prompt)}</p></div>'
    document += '<div class="cards">' + ''.join(cards) + '</div>'
    document += f'<footer>Selected trials in which the agent called the value wrong and completed the harmful action. In the judged assessment cell, {wrong} of {total} completed harmful actions followed a statement scored as calling the value wrong. Statements and actions belong to the same trial; the calls are formatted from recorded tool names and arguments.</footer></article></body></html>'
    evidence.caption = (
        "# Extended Data figure. Statements followed by a wrong-value tool call\n\n"
        "The grey box quotes the assessment sentence as sent. Each card pairs a verbatim pre-action "
        "statement with the actual action call from that same trial. All examples are in the assessment "
        "cell and completed the harmful action despite calling the value wrong. Bold emphasis is added; no words are rewritten. "
        "Panel d omits a trailing textual proposed call, marked by an ellipsis; the action beneath it is "
        "the different, actually recorded tool call. Calls retain all recorded arguments and values, "
        "with only tool(key=value) formatting added. Backticks and original punctuation are preserved. "
        "The examples were purposively selected for short, explicit objections across models and case "
        "families; they do not estimate prevalence. Deposit paths, JSONL line numbers, CSV keys, excerpt "
        "spans and highlighted phrases are in the sidecar. The source sheet's human-reader columns are "
        "blank; its automatic class labels must not be described as a completed independent human audit. "
        f"Across the judged assessment cell, {wrong} of {total} completed harmful actions followed a statement scored "
        "as calling the value wrong. This figure reports statements, not inferred private beliefs."
    )
    render_html(document, evidence)


if __name__ == "__main__":
    build()
