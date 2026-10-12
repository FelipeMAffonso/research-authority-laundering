"""Figure 1, the schematic, in the form of Betley et al.'s first figure: boxes with a coloured band for
what the model receives and a white band for what it does, thin borders, small grey column titles, one
arrow between the columns, and the spec-resistance companion site's robot above each column, the same robot on both sides.

Left, the model asked as an assistant: one box, the question with the record's potentially harmful entry in red, the
answer beneath. One arrow: the same model, the same record. Right, the model run as an agent: the turns
stacked as boxes, the system and user messages then the model's tool call, the tool result then the
model's next tool call, the executor's reply then the model's closing message; the exchange in which the
harmful action is taken is on red bands. The column titles carry the paper's measures for each arrangement,
and one line beneath the right column carries the sentence of the assessment condition and its rate.

Nothing is typed by hand: the question, the prompts, the tool calls, the executor's reply and the final
message are those of the insulin trial Figure 2 shows, read through build_fig2_trace from the deposit and
from the experiment's own scenario builder; the sentence beneath is the experiment's own; the three rates
come from PAPER-NUMBERS.json. Long texts are abridged and the abridgement is marked with […].
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDY / "experiment-2-agent-task" / "code"))
import build_fig2_trace as trace  # noqa: E402
import scenarios_new  # noqa: E402
from build_fig1_cards import GREY, RED, INK  # noqa: E402

STEM = "Fig1-schematic"
KEYS = {"identified": "e1.identification.all_cases",
        "harm": "e2.commission.all.model_weighted",
        "assess": "e3.assess.commission"}
BAND_ASKED = "#E9E8F9"      # a light tint of the paper's purple, the question put to the model
BAND_INPUT = "#EFEFEF"      # what the agent receives from the application
BAND_HARM = "#F8E1DF"       # the exchanges in which the harmful action is taken
BORDER = "#3A3A3A"

CSS = f"""
html, body {{ margin:0; background:#FFFFFF; }}
body {{ font-family: Arial, Helvetica, sans-serif; color:{INK}; -webkit-font-smoothing: antialiased; }}
.fig {{ width:1063px; box-sizing:border-box; padding:18px 24px 18px; display:grid; grid-template-columns: 392px 96px minmax(0,1fr); column-gap:14px; align-items:start; }}
.head {{ display:flex; align-items:flex-end; gap:12px; margin:0 0 10px; }}
.head svg {{ width:62px; height:72px; flex:none; }}
.title {{ font-size:11px; color:{GREY}; margin:0 0 2px; line-height:1.35; }}
.title b {{ color:{INK}; font-weight:700; }}
.box {{ border:1px solid {BORDER}; border-radius:2px; font-size:11.5px; line-height:1.45; }}
.box + .box {{ margin-top:8px; }}
.band {{ padding:6px 9px; border-bottom:1px solid {BORDER}; white-space:pre-wrap; }}
.band.asked {{ background:{BAND_ASKED}; }}
.band.input {{ background:{BAND_INPUT}; }}
.band.harm {{ background:{BAND_HARM}; }}
.does {{ padding:6px 9px; white-space:pre-wrap; background:#FFFFFF; }}
.role {{ font-weight:700; }}
.wrong {{ color:{RED}; font-weight:700; }}
.code {{ font-family:'Courier New', monospace; font-size:11px; }}
.frame {{ border:1px solid {BORDER}; border-radius:2px; padding:10px; }}
.frame .box + .box {{ margin-top:8px; }}
.arrow {{ padding-top:230px; text-align:center; }}
.arrow .lab {{ font-size:10.5px; color:{GREY}; line-height:1.3; margin-bottom:4px; }}
.foot {{ font-size:11px; color:{GREY}; margin-top:10px; line-height:1.4; }}
.foot b {{ color:{INK}; }}
"""

import robot_faces  # noqa: E402  the companion site's robot, with its faces

# one model, the same face on both sides; blue when asked as an assistant, red when run as an agent
ROBOT_ASKED = robot_faces.svg("honest", robot_faces.BLUE_BODY, robot_faces.BLUE)
ROBOT_ACTING = robot_faces.svg("honest", robot_faces.ORANGE_BODY, robot_faces.ORANGE)

ARROW_SVG = (f'<svg width="96" height="14" viewBox="0 0 96 14"><line x1="2" y1="7" x2="84" y2="7" stroke="{INK}" stroke-width="1.4"/>'
             f'<polygon points="84,2 94,7 84,12" fill="{INK}"/></svg>')


def esc(s) -> str:
    return trace.esc(s)


def abridged_record(record: str, harmful_entry: str, keep=("Blood sugar",)) -> str:
    """The record's first line, the lines named in keep, the potentially harmful entry (marked), one […] for the rest."""
    lines = [l.strip() for l in record.splitlines() if l.strip()]
    out, elided = [], False
    for i, line in enumerate(lines):
        if i == 0 or any(k in line for k in keep):
            out.append(esc(line))
        elif harmful_entry in line:
            out.append(f'<span class="wrong">{esc(line)}</span>')
        elif not elided:
            out.append("[…]"); elided = True
    return "\n".join(out)


def build() -> tuple[str, dict]:
    reg = json.loads(trace.REGISTER.read_text(encoding="utf-8"))
    bank = {c["id"]: c for c in json.loads(trace.CASES.read_text(encoding="utf-8"))}
    case = bank[trace.CASE]
    sc = scenarios_new.NEW[trace.SCENARIO]
    lookup, action = sc["world"]["lookups"][0], sc["actions"][0]
    trial = trace.deposited_trial()
    args = {k: v for k, v in trial["action_calls"][0].items() if k != "tool"}
    reply_text = json.dumps(sc["executor"]({"committed": None, "rejected": []}, action["name"], dict(args)))
    final = str(trial["final_text"])
    answer = trace.knowledge_answer_first_line()
    question = trace.knowledge_question()
    assess_sentence = scenarios_new.MECH_SENTENCES["assess"].strip()
    record_html = abridged_record(lookup["result"], case["harmful_entry"].strip())
    q_head = question.split('"')[0].strip()
    q_tail = question.rsplit('"', 1)[-1].strip()
    system_first = sc["system"].split(". ")[0] + "."
    nums = {k: reg[v] for k, v in KEYS.items()}
    pct = {k: round(v["value"]) for k, v in nums.items()}
    call = trace.call_html(action["name"], args, red_key="value")

    left = (f'<div><div class="head">{ROBOT_ASKED}<div class="title">Asked as an assistant<br><b>Identifies the entry or action as unsafe</b> in {pct["identified"]}% of answers</div></div>'
            f'<div class="box"><div class="band asked"><span class="role">User:</span> {esc(q_head)} "{record_html}" {esc(q_tail)}</div>'
            f'<div class="does"><span class="role">Assistant:</span> {esc(answer)}</div></div></div>')

    middle = f'<div class="arrow"><div class="lab">Same model,<br>same record</div>{ARROW_SVG}</div>'

    right = (f'<div><div class="head">{ROBOT_ACTING}<div class="title">Run as an agent<br><b>Completes the harmful action</b> in {pct["harm"]}% of trials</div></div>'
             '<div class="frame">'
             f'<div class="box"><div class="band input"><span class="role">System:</span> {esc(system_first)} […]\n'
             f'<span class="role">User:</span> {esc(sc["user"])}</div>'
             f'<div class="does"><span class="role">Assistant:</span> calls <span class="code">{esc(lookup["name"])}</span></div></div>'
             f'<div class="box"><div class="band harm"><span class="role">Tool result:</span> {record_html}</div>'
             f'<div class="does"><span class="role">Assistant:</span> calls <span class="code">{call}</span></div></div>'
             f'<div class="box"><div class="band harm"><span class="role">Tool result:</span> <span class="code">{esc(reply_text)}</span></div>'
             f'<div class="does"><span class="role">Assistant:</span> {esc(final)}</div></div>'
             '</div>'
             f'<div class="foot">With one sentence added to the system message, "{esc(assess_sentence)}", '
             f'<b>{pct["assess"]}% of trials</b>.</div></div>')

    page = (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'<div class="fig">{left}{middle}{right}</div></body></html>')
    sidecar = {"keys": {v: nums[k] for k, v in KEYS.items()},
               "trial": {"model": trace.MODEL, "scenario": trace.SCENARIO, "rep": trial.get("rep")},
               "texts": {"question": question, "answer": answer, "system_first_sentence": system_first, "user": sc["user"],
                         "record_abridged": re.sub(r"<[^>]+>", "", record_html), "lookup": lookup["name"],
                         "action_call": {action["name"]: args}, "executor_reply": reply_text, "final_message": final,
                         "assess_sentence": assess_sentence},
               "form": "after Betley et al. 2026, Fig. 1: banded boxes, thin borders, one arrow, no icons"}
    return page, sidecar


def main() -> None:
    page, sidecar = build()
    out = HERE / f"{STEM}.png"
    trace.render(page, out)
    (HERE / f"{STEM}.json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
