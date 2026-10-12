"""Offline support for register-backed figures."""
from __future__ import annotations

import ast
import hashlib
import html
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
STUDY = ROOT / "study"
REGISTER = STUDY / "analysis/PAPER-NUMBERS.json"
BANK = STUDY / "cases/cases.json"
PURPLE = "#5B54D6"
LAVENDER = "#D8D5F2"
GREY = "#78766F"
LIGHT = "#E8E5DD"
IVORY = "#FAF8F2"
INK = "#272721"
LINE = "#D6D2C8"
RED = "#C65343"
PIXELS = 2126
DPI = 300


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def esc(value):
    return html.escape(str(value), quote=True)


def validate_public_text(text):
    if "\u2014" in text or re.search(r"\b(committed|commission|commissions|held)\b", text, re.I):
        raise ValueError("Public text violates the author's vocabulary or punctuation rule")


def read_literal(path, name):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in statement.targets):
                return ast.literal_eval(statement.value)
    raise ValueError(f"No literal {name} in {path}")


class Evidence:
    def __init__(self, stem, adaptation):
        self.stem = stem
        self.adaptation = adaptation
        self.register = json.loads(REGISTER.read_text(encoding="utf-8"))
        self.cases = {case["id"]: case for case in json.loads(BANK.read_text(encoding="utf-8"))}
        self.reads = {}
        self.sources = []
        self.derived = []
        self.limitations = []
        self.source(REGISTER, "numeric register")
        self.caption = ""

    def source(self, path, selector, **detail):
        entry = {"path": rel(path), "sha256": sha(path), "selector": selector, **detail}
        if entry not in self.sources:
            self.sources.append(entry)
        return entry

    def entry(self, key):
        if key not in self.register:
            raise ValueError(f"Missing numeric key: {key}")
        self.reads[key] = self.register[key]
        return self.register[key]

    def number(self, key, field="value"):
        entry = self.entry(key)
        if field not in entry or entry[field] is None:
            raise ValueError(f"Missing numeric field: {key}#{field}")
        return entry[field]

    def interval(self, key):
        bounds = self.number(key, "interval")
        if len(bounds) != 2 or bounds[0] > bounds[1]:
            raise ValueError(f"Invalid interval: {key}")
        return bounds

    def optional_interval(self, key):
        entry = self.entry(key)
        if entry.get("interval") is None:
            self.limitations.append(f"No interval registered for {key}; no whisker drawn.")
            return None
        return self.interval(key)

    def case(self, case_id):
        case = self.cases[case_id]
        self.source(BANK, case_id)
        return case

    def derive(self, label, expression, keys, value):
        for key in keys:
            self.entry(key)
        self.derived.append({"label": label, "expression": expression, "keys": keys, "value": value})
        return value

    def save(self, checks=None):
        validate_public_text(self.caption)
        if "%" in self.caption:
            raise ValueError("Captions must spell out per cent")
        image_path = OUT / f"{self.stem}.png"
        with Image.open(image_path) as image:
            dimensions = list(image.size)
            dpi = image.info.get("dpi")
        payload = {
            "figure": self.stem, "adaptation": self.adaptation,
            "numeric_source": rel(REGISTER), "keys_read": sorted(self.reads),
            "number_reads": self.reads, "derivations": self.derived,
            "sources": self.sources, "limitations": self.limitations, "caption": self.caption,
            "output": {"path": rel(image_path), "sha256": sha(image_path),
                       "pixels": dimensions, "dpi": dpi,
                       "width_mm": dimensions[0] / DPI * 25.4,
                       "height_mm": dimensions[1] / DPI * 25.4},
            "checks": checks or {},
        }
        (OUT / f"{self.stem}.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        (OUT / f"{self.stem}.caption.md").write_text(self.caption + "\n", encoding="utf-8")


def style():
    arial = Path("C:/Windows/Fonts/arial.ttf")
    if not arial.exists():
        raise RuntimeError("Arial is required, not silently substituted")
    font_manager.fontManager.addfont(str(arial))
    font_manager.fontManager.addfont("C:/Windows/Fonts/arialbd.ttf")
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 8.5,
        "axes.labelsize": 8.5, "axes.titlesize": 10,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "text.color": INK, "axes.labelcolor": INK,
        "xtick.color": GREY, "ytick.color": GREY,
        "axes.edgecolor": GREY, "axes.linewidth": .65,
        "figure.facecolor": IVORY, "axes.facecolor": IVORY,
        "savefig.facecolor": IVORY, "pdf.fonttype": 42,
        "svg.fonttype": "none", "hatch.linewidth": .4,
    })


def canvas(height_mm):
    style()
    height = round(height_mm / 25.4 * DPI)
    return plt.figure(figsize=(PIXELS / DPI, height / DPI))


def axis_style(axis, ylabel, top=108):
    axis.set_ylim(0, top)
    axis.set_yticks([0, 20, 40, 60, 80, 100] if top > 100 else list(range(0, top + 1, 10)))
    axis.set_ylabel(ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines["left"].set_visible(False)
    axis.tick_params(axis="both", length=0, pad=6)
    axis.grid(axis="y", color=LINE, linewidth=.55, zorder=0)
    axis.set_axisbelow(True)


def whisker(axis, position, value, bounds):
    if bounds is not None:
        lower, upper = bounds
        axis.errorbar(position, value, yerr=[[max(0, value-lower)], [max(0, upper-value)]],
                      fmt="none", color=INK, elinewidth=.8, capsize=2.7, capthick=.8, zorder=4)


def title(figure, text, subhead=None):
    figure.text(.045, .954, text, fontsize=14, fontweight="bold", va="top")
    if subhead:
        figure.text(.045, .899, subhead, fontsize=8.5, color=GREY, va="top", linespacing=1.4)


def save_chart(figure, evidence):
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    bounds = figure.bbox
    outside = []
    texts = []
    for artist in figure.findobj(matplotlib.text.Text):
        if not artist.get_visible() or not artist.get_text():
            continue
        text = artist.get_text()
        validate_public_text(text)
        if "\u2014" in text:
            raise ValueError("Em dash in artwork")
        box = artist.get_window_extent(renderer)
        if box.width and box.height and (box.x0 < -1 or box.y0 < -1 or box.x1 > bounds.x1 + 1 or box.y1 > bounds.y1 + 1):
            outside.append(text)
        texts.append(text)
    if outside:
        raise ValueError(f"Text outside canvas: {outside}")
    figure.savefig(OUT / f"{evidence.stem}.png", dpi=DPI)
    plt.close(figure)
    evidence.save({"text_within_canvas": True, "no_em_dash": True, "visible_text": texts})


def render_html(document, evidence, width=1020):
    from playwright.sync_api import sync_playwright
    if "\u2014" in document:
        raise ValueError("Em dash in artwork")
    path = OUT / f"{evidence.stem}.html"
    path.write_text(document, encoding="utf-8")
    executables = [Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                   Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")]
    executable = next((path for path in executables if path.exists()), None)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(executable) if executable else None,
                                             headless=True, args=["--disable-background-networking"])
        context = browser.new_context(viewport={"width": width, "height": 1500},
                                      device_scale_factor=PIXELS/width)
        context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:")) else route.abort())
        page = context.new_page()
        page.goto(path.resolve().as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        checks = page.evaluate("""() => {
          const figure = document.querySelector('article');
          const bounds = figure.getBoundingClientRect();
          const overflow = [...figure.querySelectorAll('*')].filter(element => {
            if(element.closest('svg')) return false;
            const rect = element.getBoundingClientRect();
            return (element.clientWidth > 0 && element.scrollWidth > element.clientWidth + 1)
              || rect.right > bounds.right + 1 || rect.bottom > bounds.bottom + 1;
          }).map(element => element.className || element.tagName);
          return {overflow, width: bounds.width, height: bounds.height,
            font: getComputedStyle(figure).fontFamily, text: figure.innerText};
        }""")
        if checks["overflow"] or checks["height"] / width * 180 > 245:
            raise ValueError(f"Layout does not fit one page: {checks}")
        validate_public_text(checks["text"])
        page.locator("article").screenshot(path=str(OUT / f"{evidence.stem}.png"))
        browser.close()
    image_path = OUT / f"{evidence.stem}.png"
    with Image.open(image_path) as original:
        image = original.convert("RGB")
    if image.width not in (PIXELS, PIXELS+1):
        raise ValueError(f"Unexpected raster width: {image.width}")
    if image.width != PIXELS:
        image = image.resize((PIXELS, round(image.height * PIXELS/image.width)), Image.Resampling.LANCZOS)
    image.save(image_path, dpi=(DPI, DPI))
    evidence.save({**checks, "network_policy": "offline; all non-file/data requests blocked", "no_em_dash": True})
