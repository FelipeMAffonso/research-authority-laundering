"""Figure 1 as a card system, on white, one purple, no hand-drawn art.

The grammar is the overview figure of Anthropic's 9 September 2026 post (one case as four
numbered panels, three cards beside it), executed as flat cards: every box sizes to its
content, so nothing can collide; the pictograms are Google's Material Symbols (a designed
icon set, loaded from Google Fonts), never drawn by hand; the type is Arial in one scale.

Content is read, not typed: the hospital feeder card comes from fig1_content.build()
(the verbatim answer when asked, the executed call and the recorded state of a deposited
trial), the record from the case bank, and every rate from PAPER-NUMBERS.json by key.
The build refuses if the icon font did not load, so icon names can never ship as text.
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent.parent
sys.path.insert(0, str(STUDY / "paper"))
import fig1_content  # noqa: E402

REGISTER = STUDY / "analysis" / "PAPER-NUMBERS.json"
CASES = STUDY / "cases" / "cases.json"
STEM = "Fig1-cards"

# the three cards on the right: case id, family label, short title
SIDE_CASES = [
    ("N_MED_INSULIN", "Medication", "Insulin correction"),
    ("N_PHYS_DRONE", "Vehicles and instruments", "Stadium flight"),
    ("N_OFF_STRIPE_REFUND", "Payments", "Customer who owed nothing refunded"),
]
SIDE_CONSEQUENCE = {   # the case bank's catastrophe, shortened for a card
    "N_MED_INSULIN": "The patient gets 100 units of insulin for a mildly high blood sugar and goes into a coma.",
    "N_PHYS_DRONE": "A drone is flown over a full stadium under a flight ban.",
    "N_OFF_STRIPE_REFUND": "The customer who owes nothing gets the refund; the one who is owed gets nothing.",
}

PURPLE, PURPLE_TINT, GREY, RULE, RED, INK = "#5B54D6", "#EEEDFB", "#7A7A7A", "#E2E2E2", "#C8453A", "#1A1A1A"

CSS = f"""
@font-face {{ font-family:'Material Symbols Outlined'; src:url('fonts/MaterialSymbolsOutlined.ttf') format('truetype'); font-weight:100 700; font-style:normal; }}
html, body {{ margin:0; background:#FFFFFF; }}
body {{ font-family: Arial, Helvetica, sans-serif; color:{INK}; -webkit-font-smoothing: antialiased; }}
.fig {{ width:1063px; box-sizing:border-box; padding:16px 24px 16px; display:grid; grid-template-columns: 640px minmax(0,1fr); column-gap:32px; }}
.panel {{ font-size:16px; font-weight:700; margin:0 0 8px; }}
.grid {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px 22px; }}
.step {{ min-width:0; display:flex; flex-direction:column; border:1px solid {RULE}; border-radius:6px; padding:12px 14px; background:#FFFFFF; }}
.head {{ display:flex; align-items:center; gap:8px; font-size:13px; font-weight:700; }}
.num {{ width:20px; height:20px; border-radius:4px; background:{PURPLE}; color:#fff; font-size:12px; display:inline-flex; align-items:center; justify-content:center; }}
.scene {{ min-height:96px; display:flex; align-items:center; justify-content:center; gap:12px; margin:8px 0; }}
.icon {{ font-family:'Material Symbols Outlined'; font-weight:300; font-size:48px; line-height:1; color:{INK}; font-variation-settings:'FILL' 0,'wght' 300,'GRAD' 0,'opsz' 48; }}
.icon.small {{ font-size:36px; }}
.icon.purple {{ color:{PURPLE}; }}
.icon.red {{ color:{RED}; }}
.arrow {{ width:28px; height:1px; background:{INK}; position:relative; flex:none; }}
.arrow::after {{ content:''; position:absolute; right:-1px; top:-4px; border:4.5px solid transparent; border-left:7px solid {INK}; }}
.doc {{ width:150px; box-sizing:border-box; border:1px solid {INK}; border-radius:4px; padding:7px 9px; font-size:10px; line-height:1.45; background:#fff; }}
.doc .t {{ font-weight:700; margin-bottom:2px; }}
.doc .wrong {{ color:{RED}; font-weight:700; }}
.call {{ width:150px; box-sizing:border-box; border:1px solid {INK}; border-radius:4px; padding:7px 8px; font-family:'Courier New', monospace; font-size:9.5px; line-height:1.45; background:#fff; overflow-wrap:anywhere; }}
.call .wrong {{ color:{RED}; font-weight:700; }}
.cap {{ font-size:12px; line-height:1.4; margin:0 0 8px; }}
.ev {{ margin-top:auto; padding-top:8px; background:#F4F4F4; border-radius:4px; padding:7px 9px; font-size:11px; line-height:1.4; }}
.ev b {{ display:block; font-size:10.5px; color:{GREY}; font-weight:700; margin-bottom:2px; }}
.ev.answer {{ background:{PURPLE_TINT}; color:{PURPLE}; font-weight:700; }}
.ev.answer b {{ color:{PURPLE}; font-weight:700; }}
.ev code {{ font-family:'Courier New', monospace; font-size:10.5px; }}
.rate {{ margin-top:auto; padding-top:8px; font-size:13px; font-weight:700; color:{RED}; }}
.rate small {{ display:block; font-weight:400; color:{GREY}; font-size:11px; margin-top:2px; }}
.side .card {{ border-top:1px solid {RULE}; padding:12px 0 14px; }}
.side .card:first-of-type {{ border-top:none; padding-top:0; }}
.fam {{ font-size:11px; color:{GREY}; margin:0 0 3px; }}
.side h3 {{ font-size:15px; margin:0 0 6px; line-height:1.2; }}
.side p {{ font-size:12px; line-height:1.4; margin:0 0 6px; }}
.side .stat {{ font-size:12px; font-weight:700; color:{PURPLE}; }}
"""


def esc(s) -> str:
    return html.escape(str(s))


def register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def rate(reg: dict, key: str) -> tuple[str, int, int]:
    v = reg[key]
    return f"{round(v['value'])}", int(v["numerator"]), int(v["denominator"])


def record_lines(case: dict) -> str:
    wrong = case["harmful_entry"].strip()
    out = []
    for line in str(case["test_record"]).splitlines():
        line = line.strip()
        if not line:
            continue
        cls = ' class="wrong"' if line == wrong or wrong in line else ""
        out.append(f"<div{cls}>{esc(line)}</div>")
    wrong_rows = [o for o in out if "wrong" in o]
    other_rows = [o for o in out if "wrong" not in o][:3]
    return "".join([o for o in out if o in wrong_rows or o in other_rows][:4])


def call_html(call: str, wrong_value: str) -> str:
    text = esc(call)
    marker = esc(wrong_value)
    if marker and marker in text:
        text = text.replace(marker, f'<span class="wrong">{marker}</span>', 1)
    return text


def build_html(data: dict, reg: dict, bank: dict) -> tuple[str, dict]:
    feeder = next(c for c in data["cards"] if c["case"] == "N_PHYS_FEEDER")
    case = bank["N_PHYS_FEEDER"]
    r, n, d = rate(reg, "e2.catastrophe.N_PHYS_FEEDER")
    keys = {"e2.catastrophe.N_PHYS_FEEDER": reg["e2.catastrophe.N_PHYS_FEEDER"]}
    doc = f'<div class="doc">{record_lines(case)}</div>'
    wrong_value = "open" if '"open"' in feeder["call"] else case["harmful_entry"].split(":")[-1].strip()

    steps = [
        ("1", "The task and the record",
         f'<span class="icon">smart_toy</span><div class="arrow"></div>{doc}',
         "A routine maintenance request. The record the agent will read has one potentially harmful entry.",
         f'<div class="ev"><b>In the agent\'s instructions</b>{esc(case["fact_sentence"])}</div>'),
        ("2", "The lookup tool",
         f'<span class="icon small">search</span><div class="arrow"></div>{doc}',
         "The tool returns the record, that entry included. Asked about this record, the model calls the entry wrong.",
         f'<div class="ev answer"><b>{esc(feeder["model_name"])}, asked about the record</b>{esc(feeder["asked"])}</div>'),
        ("3", "The action tool",
         f'<span class="icon">smart_toy</span><div class="arrow"></div><div class="call">{call_html(feeder["call"], wrong_value)}</div>',
         "The same model, running as the agent, calls the action tool with that value.",
         f'<div class="ev"><b>The call the software executed</b><code>{esc(feeder["call"])}</code></div>'),
        ("4", "The receiving system",
         '<span class="icon red">toggle_off</span><div class="arrow"></div><span class="icon">local_hospital</span>',
         "The power-flow software opens the feeder. The hospital is left without supply.",
         f'<div class="rate">Agents completed the action in {r} per cent of trials<small>{n} of {d} test-record trials across {data["models"]} models</small></div>'),
    ]
    left = '<div class="panel">a</div><div class="grid">'
    for num, title, scene, cap, ev in steps:
        left += (f'<div class="step"><div class="head"><span class="num">{num}</span>{esc(title)}</div>'
                 f'<div class="scene">{scene}</div><p class="cap">{esc(cap)}</p>{ev}</div>')
    left += "</div>"

    right = '<div class="panel">b</div><div class="side">'
    for cid, fam, title in SIDE_CASES:
        rr, nn, dd = rate(reg, f"e2.catastrophe.{cid}")
        keys[f"e2.catastrophe.{cid}"] = reg[f"e2.catastrophe.{cid}"]
        right += (f'<div class="card"><p class="fam">{esc(fam)}</p><h3>{esc(title)}</h3>'
                  f'<p>{esc(SIDE_CONSEQUENCE[cid])}</p>'
                  f'<div class="stat">Completed the action in {rr} per cent of trials</div></div>')
    right += "</div>"

    page = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="fig"><div>{left}</div><div>{right}</div></div></body></html>'
    return page, {"keys": keys, "feeder": {k: feeder[k] for k in ("model", "model_name", "asked", "call", "readout", "system")}}


def find_chrome() -> str:
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")):
        if Path(p).exists():
            return p
    raise SystemExit("no Chrome or Edge found for rendering")


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
        ok = page.evaluate("document.fonts.check(\"48px 'Material Symbols Outlined'\")")
        if not ok:
            browser.close()
            raise SystemExit("REFUSED: the Material Symbols icon font did not load; icons would render as words")
        page.screenshot(path=str(out_png), full_page=True)
        page.pdf(path=str(out_png.with_suffix(".pdf")), width="180mm", print_background=True, prefer_css_page_size=False)
        browser.close()


def main() -> None:
    data = fig1_content.build()
    reg = register()
    bank = {c["id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    page_html, sidecar = build_html(data, reg, bank)
    out = HERE / f"{STEM}.png"
    render(page_html, out)
    (HERE / f"{STEM}.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
