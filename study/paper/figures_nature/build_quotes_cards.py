"""Extended Data Fig. 4: six verbatim statements that called the value unsafe, each followed by
the tool call that used it, as a card system on white.

The selection, the verbatim checks and the deposit lookups are the ones the earlier builder
(study/paper/figures_anthropic/build_quotes.py) established and verified; only the look is new:
white ground, one purple, Nature type sizes, the Material Symbols robot, boxes that size to
their content so nothing can collide. The build refuses if any statement or call is not
exactly what the deposits hold.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
sys.path.insert(0, str(STUDY / "paper" / "figures_anthropic"))
sys.path.insert(0, str(HERE))
import build_quotes as prior  # noqa: E402  (SELECTION, get_trial, EXPERIMENT)
from build_common import read_literal  # noqa: E402
from build_fig1_cards import find_chrome, PURPLE, PURPLE_TINT, GREY, RULE, RED, INK  # noqa: E402

import csv  # noqa: E402

STEM = "ExtData-Fig4-quotes"
REGISTER = STUDY / "analysis" / "PAPER-NUMBERS.json"

CSS = f"""
@font-face {{ font-family:'Material Symbols Outlined'; src:url('fonts/MaterialSymbolsOutlined.ttf') format('truetype'); font-weight:100 700; font-style:normal; }}
html, body {{ margin:0; background:#FFFFFF; }}
body {{ font-family: Arial, Helvetica, sans-serif; color:{INK}; -webkit-font-smoothing: antialiased; }}
.fig {{ width:1063px; box-sizing:border-box; padding:16px 24px 16px; }}
.prompt {{ background:#F4F4F4; border-radius:6px; padding:10px 14px; margin:0 0 16px; font-size:12.5px; line-height:1.45; }}
.prompt b {{ display:block; font-size:10.5px; color:{GREY}; margin-bottom:3px; }}
.cards {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px 22px; }}
.card {{ min-width:0; display:flex; flex-direction:column; border:1px solid {RULE}; border-radius:6px; padding:12px 14px; }}
.head {{ display:flex; align-items:center; gap:8px; margin-bottom:2px; }}
.letter {{ font-size:16px; font-weight:700; }}
.icon {{ font-family:'Material Symbols Outlined'; font-weight:300; font-size:26px; line-height:1; color:{INK}; font-variation-settings:'FILL' 0,'wght' 300,'GRAD' 0,'opsz' 48; }}
.model {{ font-size:13px; font-weight:700; }}
.case {{ font-size:11px; color:{GREY}; margin:0 0 8px 34px; }}
blockquote {{ font-family:'Courier New', monospace; color:{PURPLE}; font-size:11.5px; line-height:1.45; margin:0 0 10px; white-space:pre-wrap; overflow-wrap:anywhere; }}
blockquote strong {{ font-weight:700; }}
.call {{ margin-top:auto; background:#F4F4F4; border-radius:4px; padding:7px 9px; }}
.call b {{ display:block; font-size:10.5px; color:{GREY}; margin-bottom:2px; }}
.call code {{ font-family:'Courier New', monospace; font-size:10.5px; line-height:1.4; color:{INK}; overflow-wrap:anywhere; }}
"""


def esc(s) -> str:
    return html.escape(str(s))


def gather() -> tuple[str, list[dict]]:
    sheet = prior.EXPERIMENT / "SAME-TRIAL-HUMAN-READ.csv"
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        rows = {row["key"]: row for row in csv.DictReader(stream)}
    names = read_literal(STUDY / "paper/figures.py", "MODEL_NAMES")
    prompt = read_literal(prior.EXPERIMENT / "code/scenarios_new.py", "MECH_SENTENCES")["assess"].strip()
    if prompt not in (STUDY / "cases/PROMPTS-AS-SENT.md").read_text(encoding="utf-8"):
        raise SystemExit("REFUSED: the assessment sentence is not in the prompts as sent")
    bank = {c["id"]: c for c in json.loads((STUDY / "cases/cases.json").read_text(encoding="utf-8"))}
    cards = []
    for key, label, highlight, stop in prior.SELECTION:
        row = rows[key]
        if row["class as scored"] != "said wrong, committed":
            raise SystemExit(f"REFUSED: wrong class for {key}")
        deposit = json.loads((prior.EXPERIMENT / "same_trial" / f"{key}.json").read_text(encoding="utf-8"))
        if deposit["cell"] != "assess" or deposit["verdict"] != "WRONG" or not deposit["committed_harmful_value"]:
            raise SystemExit(f"REFUSED: deposit does not match for {key}")
        statement = deposit["statement"]
        if statement != row["statement before the tool call"]:
            raise SystemExit(f"REFUSED: sheet and deposit disagree for {key}")
        excerpt = statement.split(stop, 1)[0].rstrip() if stop else statement
        if highlight not in excerpt or excerpt not in statement:
            raise SystemExit(f"REFUSED: excerpt not verbatim for {key}")
        path, line_number, original = prior.get_trial(deposit["model"], key)
        if not original["acted_on_harmful_entry"] or original.get("invalid") or original.get("error"):
            raise SystemExit(f"REFUSED: original trial is not a valid completed action for {key}")
        case = bank[deposit["case"]]
        calls = []
        for action in original["action_calls"]:
            if action["tool"] != case["action"][0]:
                raise SystemExit(f"REFUSED: unexpected tool for {key}")
            params = ", ".join(f"{f}={json.dumps(v, ensure_ascii=False)}" for f, v in action.items() if f != "tool")
            calls.append(f"{action['tool']}({params})")
        cards.append({"key": key, "model": names[deposit["model"]], "label": label, "family": case["family"],
                      "excerpt": excerpt, "highlight": highlight, "truncated": bool(stop), "calls": calls,
                      "deposit": (prior.EXPERIMENT / "same_trial" / f"{key}.json").relative_to(STUDY.parent).as_posix(),
                      "original": f"{Path(path).relative_to(STUDY.parent).as_posix()} line {line_number}"})
    return prompt, cards


def build_html(prompt: str, cards: list[dict]) -> str:
    body = f'<div class="prompt"><b>The sentence added to the loop, as sent</b>{esc(prompt)}</div><div class="cards">'
    for i, c in enumerate(cards):
        quote = esc(c["excerpt"]).replace(esc(c["highlight"]), f"<strong>{esc(c['highlight'])}</strong>", 1)
        if c["truncated"]:
            quote += " […]"
        body += (f'<div class="card"><div class="head"><span class="letter">{"abcdef"[i]}</span>'
                 f'<span class="icon">smart_toy</span><span class="model">{esc(c["model"])}</span></div>'
                 f'<div class="case">{esc(c["label"])} · {esc(c["family"])}</div>'
                 f'<blockquote>{quote}</blockquote>'
                 f'<div class="call"><b>Then called the action tool</b><code>{esc("; ".join(c["calls"]))}</code></div></div>')
    body += "</div>"
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="fig">{body}</div></body></html>'


def render(page_html: str, out_png: Path) -> None:
    from playwright.sync_api import sync_playwright
    html_path = out_png.with_suffix(".html")
    html_path.write_text(page_html, encoding="utf-8")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=find_chrome(), headless=True)
        page = browser.new_page(viewport={"width": 1063, "height": 300}, device_scale_factor=2)
        page.goto(html_path.as_uri())
        page.wait_for_timeout(1500)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(800)
        if not page.evaluate("document.fonts.check(\"26px 'Material Symbols Outlined'\")"):
            browser.close()
            raise SystemExit("REFUSED: the Material Symbols icon font did not load")
        page.screenshot(path=str(out_png), full_page=True)
        page.pdf(path=str(out_png.with_suffix(".pdf")), width="180mm", print_background=True, prefer_css_page_size=False)
        browser.close()


def main() -> None:
    prompt, cards = gather()
    reg = json.loads(REGISTER.read_text(encoding="utf-8"))
    out = HERE / f"{STEM}.png"
    render(build_html(prompt, cards), out)
    sidecar = {"keys": {k: reg[k] for k in ("e3.same_trial.assess.said_unsafe_committed", "e3.same_trial.assess.commission")},
               "cards": cards, "prompt": prompt}
    (HERE / f"{STEM}.json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
