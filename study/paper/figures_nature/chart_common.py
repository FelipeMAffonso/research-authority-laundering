"""Data provenance and layout primitives for the matplotlib figures (Figs 3 and 5, Extended Data Fig. 3)."""
from __future__ import annotations

import ast
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
PAPER = OUT.parent
ROOT = PAPER.parents[1]
STUDY = ROOT / "study"
sys.path.insert(0, str(PAPER))
import figstyle
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
from PIL import Image

REGISTER = STUDY / "analysis/PAPER-NUMBERS.json"
BANK = STUDY / "cases/cases.json"
OLD = PAPER / "figures_anthropic"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def literal(path, name):
    for node in ast.parse(Path(path).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(name)


def jsonl_row(path, line_number):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for index, line in enumerate(stream, 1):
            if index == line_number:
                return json.loads(line)
    raise ValueError(f"Missing row in {path}")


class Evidence:
    def __init__(self, stem, builder):
        self.stem = stem
        self.register = json.loads(REGISTER.read_text(encoding="utf-8"))
        self.cases = {case["id"]: case for case in json.loads(BANK.read_text(encoding="utf-8"))}
        self.reads, self.sources, self.derivations = {}, [], []
        self.caption = ""
        for path in [REGISTER, PAPER / "figstyle.py", PAPER / "FIGURE-STYLE-SPEC.md", OUT / builder, Path(__file__)]:
            self.source(path, "source")

    def source(self, path, selector, **details):
        record = {"path": rel(path), "sha256": sha(path), "selector": selector, **details}
        if record not in self.sources:
            self.sources.append(record)
        return record

    def entry(self, key):
        self.reads[key] = self.register[key]
        return self.register[key]

    def number(self, key, field="value"):
        value = self.entry(key)[field]
        if value is None:
            raise ValueError(f"Missing {key}#{field}")
        return value

    def marked(self, key, field="value", fmt=","):
        value = self.number(key, field)
        return f"{value:{fmt}}<!-- num:{key} -->"

    def case(self, case_id):
        self.source(BANK, case_id)
        return self.cases[case_id]

    def old(self, stem):
        path = OLD / f"{stem}.json"
        self.source(path, "previous provenance, not numeric estimates or styling")
        return json.loads(path.read_text(encoding="utf-8"))

    def adopt(self, source):
        if sha(ROOT / source["path"]) != source["sha256"]:
            raise ValueError(f"Changed deposit: {source['path']}")
        if source not in self.sources:
            self.sources.append(source)

    def derive(self, label, expression, keys, value):
        for key in keys:
            self.entry(key)
        self.derivations.append({"label": label, "expression": expression, "keys": keys, "value": value})
        return value

    def save(self, figure):
        figure.canvas.draw()
        visible = []
        renderer = figure.canvas.get_renderer()
        for artist in figure.findobj(matplotlib.text.Text):
            if artist.get_visible() and artist.get_text():
                visible.append(artist.get_text())
                bounds = artist.get_window_extent(renderer)
                if bounds.width and bounds.height and (bounds.x0 < 0 or bounds.y0 < 0 or bounds.x1 > figure.bbox.x1+1 or bounds.y1 > figure.bbox.y1+1):
                    raise ValueError(f"Text beyond page: {artist.get_text()}")
        for text in [*visible, re.sub(r"<!--.*?-->", "", self.caption)]:
            if "\u2014" in text or re.search(r"\b(committed|commission|held)\b", text, re.I):
                raise ValueError("Disallowed public wording")
        if re.search(r"\b(files?|keys?|registers?|sidecars?|builders?|selection)\b", re.sub(r"<!--.*?-->", "", self.caption), re.I):
            raise ValueError("Provenance commentary in caption")
        width, height = figure.get_size_inches()
        inset = .02
        figure.add_artist(Rectangle((inset/width,.5), 1-2*inset/width, 0,
                                    transform=figure.transFigure, fill=False, edgecolor=figstyle.WHITE, linewidth=0))
        staging = OUT / "_render"
        figstyle.save(figure, self.stem, staging)
        for suffix in ("png", "pdf"):
            (staging / f"{self.stem}.{suffix}").replace(OUT / f"{self.stem}.{suffix}")
        outputs = {}
        for suffix in ("png", "pdf"):
            path = OUT / f"{self.stem}.{suffix}"
            outputs[suffix] = {"path": rel(path), "sha256": sha(path)}
        with Image.open(OUT / f"{self.stem}.png") as image:
            outputs["png"].update(pixels=list(image.size), dpi=image.info.get("dpi"))
        payload = {"figure": self.stem, "keys_read": sorted(self.reads), "number_reads": self.reads,
                   "sources": self.sources, "derivations": self.derivations, "caption": self.caption,
                   "outputs": outputs, "checks": {"text_within_canvas": True, "visible_text": visible,
                                                  "public_vocabulary": True, "caption_no_provenance": True},
                   "intended_mm": [width*25.4,height*25.4]}
        (OUT / f"{self.stem}.json").write_text(json.dumps(payload,ensure_ascii=True,indent=2)+"\n",encoding="utf-8")
        (OUT / f"{self.stem}.caption.md").write_text(self.caption+"\n",encoding="utf-8")


def errorbar(axis, position, value, interval):
    lower, upper = interval
    axis.errorbar(position, value, yerr=[[max(0,value-lower)],[max(0,upper-value)]], fmt="none", color=figstyle.INK, **figstyle.whisker_kw())


def mm_axis(figure, width, height):
    axis = figure.add_axes([0,0,1,1])
    axis.set_xlim(0,width)
    axis.set_ylim(height,0)
    figstyle.clean(axis)
    axis.set_axis_off()
    return axis


def rich_text(axis, text, x, y, width, *, mono=False, bold_phrase=None, red_phrase=None, colour=None):
    figure = axis.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    pixels_per_mm = axis.transData.transform((1,0))[0]-axis.transData.transform((0,0))[0]
    family = "Courier New" if mono else figstyle.FONT
    spans = []
    for phrase, kind in [(bold_phrase,"bold"),(red_phrase,"red")]:
        if phrase:
            start = text.index(phrase)
            spans.append((start,start+len(phrase),kind))
    cursor, baseline = x, y
    leading = figstyle.PT_LABEL*1.24/72*25.4
    for match in re.finditer(r"\n|[^\S\n]+|[^\s]+", text):
        token = match.group()
        if token == "\n":
            cursor, baseline = x, baseline+leading
            continue
        bold = any(start < match.end() and end > match.start() and kind == "bold" for start,end,kind in spans)
        red = any(start < match.end() and end > match.start() and kind == "red" for start,end,kind in spans)
        properties = FontProperties(family=family, size=figstyle.PT_LABEL, weight="bold" if bold else "normal")
        length = renderer.get_text_width_height_descent(token,properties,ismath=False)[0]/pixels_per_mm
        if cursor+length > x+width and cursor > x:
            cursor, baseline = x, baseline+leading
            if token.isspace():
                continue
        if length > width+.1:
            raise ValueError(f"Unbreakable text exceeds column: {token}")
        if not token.isspace():
            axis.text(cursor,baseline,token,fontproperties=properties,va="top",ha="left",
                      color=figstyle.RED if red else (colour or figstyle.INK),parse_math=False)
        cursor += length
    return baseline+leading


def box(axis, text, x, top, width, height, *, tint=None, mono=False, bold_phrase=None, red_phrase=None):
    axis.add_patch(Rectangle((x,top),width,height,facecolor=tint or figstyle.WHITE,
                             edgecolor=figstyle.GREY,linewidth=figstyle.LINE))
    end = rich_text(axis,text,x+1.7,top+1.8,width-3.4,mono=mono,bold_phrase=bold_phrase,red_phrase=red_phrase)
    if end > top+height-1:
        raise ValueError(f"Box text overflows by {end-top-height+1:.1f} mm: {text}")
    return end
