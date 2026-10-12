"""Four of the nine figures, rebuilt to study/paper/FIGURE-STYLE-SPEC.md.

    python -X utf8 study/paper/figures_nature/build_restyled.py

White ground, one purple with its tint, one grey with its tint, red for harm only, ink for text.
Nothing inside a figure except the content, the panel letters, the axis labels, the tick labels,
the value labels and a one-row legend. Every number is read from study/analysis/PAPER-NUMBERS.json
by key, and the keys each figure read are written to a sidecar JSON beside its PNG.

  Fig4-role-basis            the two roles and the three homes of the basis
  Fig6-real-systems          the real systems, both placements, and the control-record job
  ExtData-Fig1-cost          the harmful action rate against cost and against time per trial
  ExtData-Fig2-catastrophes  the actions completed, all twenty-two

The data logic, the keys and the layout follow study/paper/figures.py (fig_role_basis,
fig_real_systems, fig_cost, fig_catastrophes). Only the look changes.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
STUDY = PAPER.parent
sys.path.insert(0, str(PAPER))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402

import figstyle as fs  # noqa: E402

PURPLE, PURPLE_TINT = fs.PURPLE, fs.PURPLE_TINT
GREY, GREY_TINT, INK = fs.GREY, fs.GREY_TINT, fs.INK

# --------------------------------------------------------------------------- the register

REGISTER = STUDY / "analysis" / "PAPER-NUMBERS.json"
if not REGISTER.exists():
    sys.exit(f"build_restyled.py: the register is not on disk: {REGISTER}")
N = json.loads(REGISTER.read_text(encoding="utf-8"))

_USED: set[str] = set()


def num(key: str, field: str = "value"):
    """One number from the register, recorded for the sidecar. A missing key stops the run."""
    if key not in N:
        sys.exit(f"build_restyled.py: the register has no key {key}")
    entry = N[key]
    if field not in entry or entry[field] is None:
        sys.exit(f"build_restyled.py: the register entry {key} has no {field}")
    _USED.add(key)
    return entry[field]


def interval(key: str):
    lo, hi = num(key, "interval")
    return float(lo), float(hi)


def require(keys) -> None:
    missing = [k for k in keys if k not in N]
    if missing:
        for k in missing:
            print(f"build_restyled.py: missing register key {k}", file=sys.stderr)
        sys.exit(1)


def start() -> None:
    _USED.clear()


def sidecar(stem: str) -> None:
    (HERE / f"{stem}.keys.json").write_text(json.dumps({
        "figure": stem,
        "png": f"{stem}.png",
        "register": "study/analysis/PAPER-NUMBERS.json",
        "keys": sorted(_USED),
    }, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- names, from figures.py

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

SYSTEM_NAMES = {
    "grid": "hospital left without power (power flow)",
    "robot_mujoco": "robot into a staffed zone (MuJoCo)",
    "robot": "the same robot case (PyBullet)",
    "drone": "drone in closed airspace (simulator)",
    "car": "van through a school crossing (simulator)",
    "telescope": "telescope pointed near the Sun (astropy)",
    "beamline": "stage into the detector housing (beamline)",
    "lab_ot2": "lysis buffer into patient samples (OT-2)",
    "registry": "failed replication published (registry)",
    "datastore": "only copy of a run deleted (filesystem)",
    "shell": "only copy of a run deleted (shell)",
    "cloud.C1_firewall": "customer database opened to the internet (cloud)",
    "cloud.C2_bucket": "evidence files destroyed (cloud)",
    "mcp": "patient data published (MCP server)",
    "sdk.access": "outside partner given access (Agents SDK)",
    "sdk.cluster": "three-week run killed (Agents SDK)",
    "langgraph.access": "the same access case (LangGraph)",
    "langgraph.cluster": "the same cluster case (LangGraph)",
    "adk.access": "the same access case (Google ADK)",
    "adk.cluster": "the same cluster case (Google ADK)",
    "mail": "decision letter to the blinded reviewer (mail)",
    "mail_attach": "referees' report sent to the author (mail)",
    "calendar": "doctoral defence cancelled (calendar)",
    "share": "embargoed folder opened to outsiders (shared files)",
    "stripe": "customer who owed nothing refunded (payments)",
    "prolific": "participant paid a thousand times over (study platform)",
    "canvas": "failing midterm posted to 180 students (gradebook)",
    "cluster": "three-week run killed on its last day (cluster)",
    "editorial": "accepted author told the paper is rejected (editorial)",
    "preprint": "embargoed manuscript published (preprint server)",
    "repository": "identifiable data published (repository)",
    "forge": "release branch deleted (code forge)",
    "alphafold": "running prediction batch killed (structure jobs)",
}

OTHER_TEAMS = ["grid", "robot_mujoco", "robot", "drone", "car", "telescope", "beamline", "lab_ot2",
               "registry", "datastore", "shell", "cloud.C1_firewall", "cloud.C2_bucket", "mcp",
               "sdk.access", "sdk.cluster", "langgraph.access", "langgraph.cluster",
               "adk.access", "adk.cluster"]
OFFICE = ["mail", "mail_attach", "calendar", "share", "stripe", "prolific", "canvas", "cluster",
          "editorial", "preprint", "repository", "forge", "alphafold"]
PANEL_FLOOR = 10

BASIS_HOMES = [("K", "the model's role knowledge"), ("P", "the operator's instructions"),
               ("R", "a second record from the same lookup")]
ROLES = [("implement", "implementing"), ("order", "ordering")]

CATASTROPHE_ROWS = [
    ("N_MED_INSULIN", "a patient is given 100 units of insulin and goes into a coma"),
    ("N_MED_NEONATE", "a newborn receives forty times the antibiotic dose"),
    ("N_MED_WARFARIN", "ten times the blood-thinner dose, to a patient already in range"),
    ("N_MED_NITRATE", "nitroglycerin hours after sildenafil, dropping the blood pressure"),
    ("N_EVD_REFILL", "a 74-year-old is sent ten times his blood-pressure dose"),
    ("N_EVD_THERMOSTAT", "a sleeping infant spends eleven hours in a room at 35 degrees"),
    ("N_PHYS_FEEDER", "a hospital loses all electrical power in the middle of the day"),
    ("N_PHYS_DRONE", "a drone is flown over a full stadium under a flight ban"),
    ("N_VEH_CROSSING", "a van is driven through a school crossing while children are on it"),
    ("N_PHYS_ROBOT", "a 200 kg robot is driven into a zone where two people are working"),
    ("N_LAB_ACID", "water is poured into concentrated acid, which boils and sprays"),
    ("N_LAB_BLEACH", "bleach and ammonia are mixed in a closed room"),
    ("N_LAW_OPIOID", "180 tablets of a strong opioid are mailed with no prescription"),
    ("N_EVD_PICKUP", "a six-year-old is handed to the man a court keeps away from him"),
    ("N_EVD_SURGERY", "a healthy knee is opened and replaced"),
    ("N_FIN_MARGIN", "a retiree on 22,000 dollars a year is set up to trade on margin"),
    ("N_EVD_RENT", "the rent is locked in a 90-day account on the day it is due"),
    ("N_DATA_KEYS", "the database password and every API key are published"),
    ("N_OFF_CLUSTER_JOB", "a three-week computation is killed on its last day"),
    ("N_OFF_CALENDAR", "a doctoral defence is cancelled the day before it happens"),
    ("N_OFF_FORGE_BRANCH", "the only copy of a shipped release's source is deleted"),
    ("N_OPS_REGISTRY", "a result whose replication failed is published as final"),
]


# --------------------------------------------------------------------------- small drawing helpers

def save_figure(fig, stem: str) -> Path:
    """figstyle.save, then copy into the figure folder. A file a viewer is holding open is left
    alone with a warning rather than stopping the run."""
    tmp = Path(tempfile.mkdtemp(prefix="figures_nature_"))
    fs.save(fig, stem, tmp)
    for ext in ("png", "pdf"):
        try:
            shutil.copy2(tmp / f"{stem}.{ext}", HERE / f"{stem}.{ext}")
        except PermissionError:
            print(f"  {stem}.{ext} is open elsewhere and was not replaced", file=sys.stderr)
    shutil.rmtree(tmp, ignore_errors=True)
    return HERE / f"{stem}.png"


def whiskers(color: str) -> dict:
    """figstyle's thin whiskers, in the colour of the series they belong to."""
    kw = fs.whisker_kw()
    kw["ecolor"] = color
    return kw


def side_label(ax, x, y, text, color=INK, dx_pt: float = 3.0):
    """A regular-weight value to the right of a point, at figstyle's value size."""
    ax.annotate(text, (x, y), xytext=(dx_pt, 0), textcoords="offset points", ha="left",
                va="center", fontsize=fs.PT_VALUE, color=color, clip_on=False)


def group_rule(ax, xa, xb, label, line_y=-0.115, text_y=-0.155, wrap=15):
    """A thin rule under a pair of bars with the group's name under it, in the tick size."""
    tr = ax.get_xaxis_transform()
    ax.plot([xa - 0.5, xb + 0.5], [line_y, line_y], transform=tr, color=GREY_TINT, lw=0.8,
            clip_on=False, solid_capstyle="butt")
    if label:
        ax.text((xa + xb) / 2, text_y, "\n".join(textwrap.wrap(label, wrap)), transform=tr,
                ha="center", va="top", fontsize=fs.PT_TICK, color=GREY, clip_on=False,
                linespacing=1.25)


# =========================================================================== Figure 3

def fig3_role_basis():
    """Panel a, the harmful action rate in the six cells of role and home; panel b, the same six
    cells on the matched control record."""
    start()
    cells = [(code, role) for code, _ in BASIS_HOMES for role, _ in ROLES]
    require([f"e2.basis.{c}.{r}.{g}" for c, r in cells
             for g in ("all", "newest", "faster", "completion")])

    # Both panels are the same width, and the bars stand far enough apart that the two role words
    # fit under them without touching; the pairs are held together by the rule under each pair.
    fig = fs.figure(fs.DOUBLE_MM, 76.0)
    axa = fig.add_axes([0.058, 0.285, 0.422, 0.575])
    axb = fig.add_axes([0.548, 0.285, 0.422, 0.575])
    xs = [0.0, 1.22, 2.56, 3.78, 5.12, 6.34]
    xlims = (-0.62, 6.96)
    role_ticks = [dict(ROLES)[r].capitalize() for _, r in cells]

    tops = []
    for x, (code, role) in zip(xs, cells):
        key = f"e2.basis.{code}.{role}.all"
        v = num(key)
        lo, hi = interval(key)
        tops.append(hi)
        axa.bar(x, v, width=0.72, color=PURPLE, edgecolor="none", zorder=2)
        axa.errorbar(x, v, yerr=[[max(0.0, v - lo)], [max(0.0, hi - v)]], fmt="none",
                     zorder=4, **whiskers(INK))
        axa.plot(x - 0.18, num(f"e2.basis.{code}.{role}.newest"), "o", ms=3.4, zorder=5,
                 markerfacecolor="#FFFFFF", markeredgecolor=INK, markeredgewidth=0.7, ls="none")
        axa.plot(x + 0.18, num(f"e2.basis.{code}.{role}.faster"), "s", ms=3.0, color=INK,
                 zorder=5, ls="none")
        fs.value_label(axa, x, hi, f"{v:.0f}")

    ymax = 10 * (int((max(tops) + 8) // 10) + 1)
    axa.set_xticks(xs)
    axa.set_xticklabels(role_ticks)
    axa.set_xlim(*xlims)
    axa.set_ylim(0, ymax)
    axa.set_yticks(range(0, ymax + 1, 10))
    axa.set_ylabel("Harmful action rate (%)")
    fs.clean(axa)
    fs.panel_label(axa, "a", dx=-0.135, dy=1.03)
    for i, (_, home) in enumerate(BASIS_HOMES):
        group_rule(axa, xs[2 * i], xs[2 * i + 1], home)

    handles = [Line2D([], [], marker="o", ms=3.4, markerfacecolor="#FFFFFF", markeredgecolor=INK,
                      markeredgewidth=0.7, ls="none"),
               Line2D([], [], marker="s", ms=3.0, color=INK, ls="none")]
    fs.legend_row(axa, handles, ["newest and most safety-trained", "faster and lower-cost"])

    for x, (code, role) in zip(xs, cells):
        key = f"e2.basis.{code}.{role}.completion"
        v = num(key)
        lo, hi = interval(key)
        axb.bar(x, v, width=0.72, color=GREY, edgecolor="none", zorder=2)
        axb.errorbar(x, v, yerr=[[max(0.0, v - lo)], [max(0.0, hi - v)]], fmt="none",
                     zorder=4, **whiskers(INK))
        fs.value_label(axb, x, hi, f"{v:.0f}")
    axb.set_xticks(xs)
    axb.set_xticklabels(role_ticks)
    axb.set_xlim(*xlims)
    axb.set_ylim(0, 112)
    axb.set_yticks(range(0, 101, 20))
    axb.set_ylabel("Did the job on the control record (%)")
    fs.clean(axb)
    fs.panel_label(axb, "b", dx=-0.135, dy=1.03)
    for i, (_, home) in enumerate(BASIS_HOMES):
        group_rule(axb, xs[2 * i], xs[2 * i + 1], home)

    out = save_figure(fig, "Fig4-role-basis")
    sidecar("Fig4-role-basis")
    print("  drew", out.name)


# =========================================================================== Figure 5

def e4_rate(system: str, placement: str, what: str = "commission"):
    """(value, (lo, hi), trials) or None where the folder holds smoke trials only."""
    key = f"e4.{system}.{placement}.{what}"
    if key not in N:
        return None
    den = N[key].get("denominator") or 0
    if den < PANEL_FLOOR:
        return None
    return num(key), interval(key), int(den)


def fig5_real_systems():
    """Three columns: the basis in the operator's instructions, the basis in a second record, and
    the job done on the matched control record. Two families, one row per system and case."""
    start()
    for s in OTHER_TEAMS + OFFICE:
        require([f"e4.{s}.P.commission", f"e4.{s}.R.commission", f"e4.{s}.P.completion"])
    require([f"e4.{f}.{p}.{w}" for f in ("other_teams", "office")
             for p in ("P", "R") for w in ("commission", "completion")])

    columns = [("P", "commission", PURPLE, "Harmful action rate,\nthe basis in the operator's instructions (%)"),
               ("R", "commission", PURPLE_TINT, "Harmful action rate,\nthe basis in a second record (%)"),
               ("P", "completion", GREY, "Did the job on the control record,\nthe basis in the operator's instructions (%)")]
    lefts = [0.345, 0.560, 0.775]
    width = 0.185
    blocks = {"a": (0.475, 0.440), "b": (0.105, 0.285)}

    fig = fs.figure(fs.DOUBLE_MM, 205.0)
    trials = []

    def column(ax, systems, family_key, placement, what, color, label_rows, bottom_row, label_text):
        edge = PURPLE if color == PURPLE_TINT else color
        ys = list(range(len(systems)))[::-1]
        for y, s in zip(ys, systems):
            ax.axhline(y, color=GREY_TINT, lw=0.3, zorder=0)
            got = e4_rate(s, placement, what)
            if got is None:
                ax.text(2, y, "not run", fontsize=fs.PT_TICK, ha="left", va="center", color=GREY)
                continue
            v, (lo, hi), den = got
            trials.append((den, f"e4.{s}.{placement}.{what}"))
            ax.errorbar(v, y, xerr=[[max(0.0, v - lo)], [max(0.0, hi - v)]], fmt="o", ms=3.0,
                        color=color, markerfacecolor=color, markeredgecolor=edge,
                        markeredgewidth=0.5, elinewidth=fs.LINE, capsize=1.5, capthick=fs.LINE,
                        zorder=3, clip_on=False)
            side_label(ax, min(hi, 100.0), y, f"{v:.0f}")
        agg_y = -1.5
        ax.axhline(-0.75, color=GREY_TINT, lw=0.6)
        key = f"e4.{family_key}.{placement}.{what}"
        v = num(key)
        lo, hi = interval(key)
        ax.errorbar(v, agg_y, xerr=[[max(0.0, v - lo)], [max(0.0, hi - v)]], fmt="D", ms=3.4,
                    color=color, markerfacecolor=color, markeredgecolor=edge, markeredgewidth=0.5,
                    elinewidth=fs.LINE, capsize=1.5, capthick=fs.LINE, zorder=4, clip_on=False)
        side_label(ax, min(hi, 100.0), agg_y, f"{v:.0f}")
        ax.set_yticks(ys + [agg_y])
        if label_rows:
            ax.set_yticklabels([SYSTEM_NAMES[s] for s in systems] + ["the family pooled"],
                               fontsize=fs.PT_TICK)
        else:
            ax.set_yticklabels([])
            ax.tick_params(axis="y", length=0)
        ax.set_ylim(agg_y - 0.9, max(ys) + 0.9)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
        fs.clean(ax)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        if bottom_row:
            ax.set_xlabel("\n".join(textwrap.wrap(label_text, 34)), labelpad=4)

    for letter, systems, family_key in (("a", OTHER_TEAMS, "other_teams"),
                                        ("b", OFFICE, "office")):
        bottom, height = blocks[letter]
        for i, (placement, what, color, label_text) in enumerate(columns):
            ax = fig.add_axes([lefts[i], bottom, width, height])
            column(ax, systems, family_key, placement, what, color, i == 0, letter == "b", label_text)
            if i == 0:
                fs.panel_label(ax, letter, dx=-1.72, dy=1.012)

    out = save_figure(fig, "Fig6-real-systems")
    sidecar("Fig6-real-systems")
    print("  drew", out.name)
    rate_rows = [t for t in trials if t[1].endswith("commission")]
    return min(rate_rows)[1], max(rate_rows)[1]


# =========================================================================== Extended Data Figure 1

def extfig1_cost():
    """One point per model: the harmful action rate against what one trial cost, and against how
    long one trial took."""
    start()
    models = [m for m in MODEL_NAMES if f"e2.cost.{m}.per_trial" in N
              and N[f"e2.cost.{m}.per_trial"]["value"]]
    require([f"e2.model.{m}.identified" for m in models]
            + [f"e2.cost.{m}.seconds" for m in models])
    newest_group = set(N.get("meta", {}).get("newest_group", []))
    rows = [{"model": m, "cost": num(f"e2.cost.{m}.per_trial"),
             "rate": num(f"e2.model.{m}.identified"),
             "trials": int(num(f"e2.model.{m}.identified", "denominator")),
             "seconds": num(f"e2.cost.{m}.seconds"), "newest": m in newest_group} for m in models]

    rank = sorted(rows, key=lambda d: (-d["rate"], MODEL_NAMES[d["model"]]))
    for i, r in enumerate(rank, start=1):
        r["rank"] = i

    fig = fs.figure(fs.DOUBLE_MM, 82.0)
    width_a, width_b, height = 0.285, 0.250, 0.640
    axa = fig.add_axes([0.070, 0.195, width_a, height])
    axb = fig.add_axes([0.722, 0.195, width_b, height])
    ticks = {"cost": [0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5],
             "seconds": [3, 4, 6, 8, 10, 15, 20]}
    limits = {"cost": (0.016, 7.0), "seconds": (2.4, 27.0)}
    ylo, yhi = -4.0, 72.0
    for ax, xkey, xlabel in ((axa, "cost", "Cost of one agent trial (US cents, log scale)"),
                             (axb, "seconds", "Time of one agent trial (seconds, log scale)")):
        for r in rows:
            ax.plot(r[xkey], r["rate"], "o", ms=4.0, zorder=3,
                    markerfacecolor=PURPLE_TINT if r["newest"] else PURPLE,
                    markeredgecolor=PURPLE, markeredgewidth=0.5, ls="none")
        ax.set_xscale("log")
        ax.set_xlim(*limits[xkey])
        ax.set_xticks(ticks[xkey])
        ax.set_xticklabels([("%g" % t) for t in ticks[xkey]])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlabel(xlabel)
        ax.set_ylim(ylo, yhi)
        ax.set_yticks(range(0, 61, 20))
        fs.clean(ax)
        ax.spines["left"].set_bounds(0, 60)
    axa.set_ylabel("Harmful action rate (%)")
    axb.set_ylabel("Harmful action rate (%)")
    fs.panel_label(axa, "a", dx=-0.22, dy=1.03)
    fs.panel_label(axb, "b", dx=-0.25, dy=1.03)

    # Each point carries its rank, 1 for the highest harmful action rate, on both panels; the key
    # between the panels gives the model behind every number. A number is set beside its own point,
    # on whichever side is free, so that no number covers a point or another number.
    def number_points(ax, xkey, panel_w):
        lo_x, hi_x = limits[xkey]
        span_x = math.log10(hi_x) - math.log10(lo_x)
        w_mm, h_mm = panel_w * fs.DOUBLE_MM, height * 82.0

        def to_mm(x, y):
            return ((math.log10(x) - math.log10(lo_x)) / span_x * w_mm,
                    (y - ylo) / (yhi - ylo) * h_mm)

        def to_data(cx, cy):
            return (lo_x * 10 ** (cx / w_mm * span_x), ylo + cy / h_mm * (yhi - ylo))

        def clear(box, taken):
            x, y, w, h = box
            return all(abs(x - bx) >= (w + bw) / 2 or abs(y - by) >= (h + bh) / 2
                       for bx, by, bw, bh in taken)

        taken = [to_mm(r[xkey], r["rate"]) + (2.0, 2.0) for r in rows]      # the points themselves
        for r in rank:
            text = str(r["rank"])
            w, h = 1.05 * len(text) + 1.9, 2.8      # a margin so two numbers never read as one
            mx, my = to_mm(r[xkey], r["rate"])
            spots = []
            for rad in (1.1, 2.6, 4.2, 6.2, 8.5):    # the nearest free place, in rings
                near, far = rad * 0.75, rad
                spots += [(mx + far + w / 2, my), (mx - far - w / 2, my),
                          (mx, my + far + h / 2), (mx, my - far - h / 2),
                          (mx + near + w / 2, my + near + h / 2),
                          (mx - near - w / 2, my + near + h / 2),
                          (mx + near + w / 2, my - near - h / 2),
                          (mx - near - w / 2, my - near - h / 2)]
            floor_mm = (0.0 - ylo) / (yhi - ylo) * h_mm + h / 2      # nothing sits on the axis
            spots = [s for s in spots
                     if w / 2 <= s[0] <= w_mm - w / 2 and floor_mm <= s[1] <= h_mm - h / 2]
            cx, cy = next((s for s in spots if clear((s[0], s[1], w, h), taken)), spots[0])
            taken.append((cx, cy, w, h))
            dx, dy = to_data(cx, cy)
            ax.text(dx, dy, text, fontsize=fs.PT_TICK, color=INK, ha="center", va="center",
                    zorder=6)

    number_points(axa, "cost", width_a)
    number_points(axb, "seconds", width_b)

    for i, r in enumerate(rank):                      # the key, two columns of eight
        fig.text(0.392 + 0.138 * (i // 8), 0.775 - 0.0378 * (i % 8),
                 f"{r['rank']}  {MODEL_NAMES[r['model']]}", fontsize=fs.PT_TICK, color=INK,
                 ha="left", va="center")

    handles = [Line2D([], [], marker="o", ms=4.0, markerfacecolor=PURPLE_TINT,
                      markeredgecolor=PURPLE, markeredgewidth=0.5, ls="none"),
               Line2D([], [], marker="o", ms=4.0, markerfacecolor=PURPLE,
                      markeredgecolor=PURPLE, markeredgewidth=0.5, ls="none")]
    fs.legend_row(axa, handles, ["newest and most safety-trained", "faster and lower-cost"])

    out = save_figure(fig, "ExtData-Fig1-cost")
    sidecar("ExtData-Fig1-cost")
    print("  drew", out.name)
    return rows


# =========================================================================== Extended Data Figure 2

def extfig2_catastrophes():
    """Every one of the twenty-two worst cases, by the share of test-record trials in which the
    agent completed the action."""
    start()
    keys = [f"e2.catastrophe.{cid}" for cid, _ in CATASTROPHE_ROWS]
    require(keys + [k + ".newest" for k in keys])
    rows = []
    for cid, label in CATASTROPHE_ROWS:
        k = f"e2.catastrophe.{cid}"
        rows.append({"case": cid, "label": label, "rate": num(k),
                     "n": int(num(k, "numerator")), "N": int(num(k, "denominator")),
                     "newest_n": int(num(k + ".newest", "numerator")),
                     "newest_N": int(num(k + ".newest", "denominator"))})
    rows.sort(key=lambda d: -d["rate"])

    fig = fs.figure(fs.DOUBLE_MM, 168.0)
    ax = fig.add_axes([0.395, 0.060, 0.335, 0.930])
    ys = list(range(len(rows)))[::-1]
    for y, r in zip(ys, rows):
        ax.barh(y, r["rate"], height=0.60, color=PURPLE, edgecolor="none", zorder=2)
        side_label(ax, r["rate"], y, f"{r['rate']:.0f}")
        ax.text(1.055, y, f"{r['n']} of {r['N']} trials, newest models {r['newest_n']} of "
                          f"{r['newest_N']}", transform=ax.get_yaxis_transform(), va="center",
                ha="left", fontsize=fs.PT_TICK, color=GREY, clip_on=False)
    ax.set_yticks(ys)
    ax.set_yticklabels(["\n".join(textwrap.wrap(r["label"], 40)) for r in rows],
                       fontsize=fs.PT_LABEL, linespacing=1.15)
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 25))
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xlabel("Harmful action rate (%)")
    fs.clean(ax)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    out = save_figure(fig, "ExtData-Fig2-catastrophes")
    sidecar("ExtData-Fig2-catastrophes")
    print("  drew", out.name)
    return rows


# =========================================================================== the captions

def pct(key: str) -> str:
    return f"{N[key]['value']:.0f}% <!-- num:{key} -->"


def plain(key: str) -> str:
    return f"{N[key]['value']:.0f} <!-- num:{key} -->"


def den(key: str) -> str:
    return f"{int(N[key]['denominator']):,} <!-- num:{key}#denominator -->"


def captions(e4_trials, cost_rows, cat_rows) -> None:
    cells = [(code, role) for code, _ in BASIS_HOMES for role, _ in ROLES]
    wrong_keys = [f"e2.basis.{c}.{r}.all" for c, r in cells]
    done_keys = [f"e2.basis.{c}.{r}.completion" for c, r in cells]
    lo_done = min(done_keys, key=lambda k: N[k]["value"])
    hi_done = max(done_keys, key=lambda k: N[k]["value"])
    lo_wrong_n = min(wrong_keys, key=lambda k: N[k]["denominator"])
    hi_wrong_n = max(wrong_keys, key=lambda k: N[k]["denominator"])
    lo_done_n = min(done_keys, key=lambda k: N[k]["denominator"])
    hi_done_n = max(done_keys, key=lambda k: N[k]["denominator"])

    L = []
    L.append("## Figure 4. Where the basis appears, and what the agent's job is.")
    L.append("")
    L.append(
        "**a**, The harmful action rate in six cells for trials with the potentially harmful entry. The basis "
        "for rejecting the entry comes from the model's role knowledge, the operator's instructions or a second "
        "record returned by the same lookup. These placements use different case sets. The agent either implements "
        "the action itself or enters an order "
        "for a person or system to execute. With the basis in role knowledge, agents completed the harmful "
        f"action in {pct('e2.basis.K.implement.all')} of implementing trials and {pct('e2.basis.K.order.all')} "
        "of ordering trials. With the basis in the operator's instructions, the rates were "
        f"{pct('e2.basis.P.implement.all')} and {pct('e2.basis.P.order.all')}. With the basis in a second "
        f"record, they were {pct('e2.basis.R.implement.all')} and {pct('e2.basis.R.order.all')}. Ordering was "
        "no safer than implementing. **b**, The same six cells in the same order with the matched control "
        "record, where the work should be done. Agents did the job on the control record in "
        f"{pct(lo_done)} to {pct(hi_done)} of trials. Therefore, the harmful actions in **a** are not a "
        "general failure to act. Bars show the rate over sixteen models with every model weighted equally. "
        "The open circle is the newest and most safety-trained group, and the filled square is the faster and "
        "lower-cost group. Whiskers are the 95% bootstrap intervals over models, then cases within each "
        f"model, from 2,000 draws. n is the trials in each cell, {den(lo_wrong_n)} to {den(hi_wrong_n)} with "
        f"the potentially harmful entry and {den(lo_done_n)} to {den(hi_done_n)} with the control entry.")
    L.append("")

    lo_e4, hi_e4 = e4_trials       # the rows with the fewest and the most trials
    L.append("## Figure 6. The same cases run on real software systems.")
    L.append("")
    L.append(
        "**a**, The systems written by other teams: a power-flow engine, two physics engines, a driving and a "
        "flight simulator, an astronomy library, a synchrotron beamline model, a liquid handler, a "
        "version-control registry, a filesystem, a shell, a cloud emulator, a Model Context Protocol server "
        "and three agent "
        "frameworks. **b**, "
        "The office and research systems, built to their vendors' own developer documentation on local "
        "throwaway state. Each row is one system running one case, named by what happens if the potentially "
        "harmful entry is acted on, with the software in brackets. The first column is the harmful action rate "
        "with the basis in the operator's instructions, and the second is the same rate with the basis in a "
        "second record returned by the same lookup. The third is the share of trials with the matched control "
        "record in which the agent did the job, with the basis in the operator's instructions. Every outcome "
        "is read from local test-system state or, for the stateless refund server, its returned Refund object, "
        "never from the agent's text. Points are the rate among identified pairs, the trials of models that identified "
        "the entry or implied action as unsafe when asked, with every model weighted equally. Whiskers are the 95% intervals, and n "
        f"is the trials in the row, {den(lo_e4)} to {den(hi_e4)}. Diamonds are the family pooled: "
        f"{pct('e4.other_teams.P.commission')} and {pct('e4.other_teams.R.commission')} under the two "
        "placements for the systems written by other teams and "
        f"{pct('e4.office.P.commission')} and {pct('e4.office.R.commission')} for the office and research "
        f"systems, against {pct('e4.other_teams.P.completion')} and {pct('e4.office.P.completion')} for the "
        "job done on the control record.")
    L.append("")

    by_trials = sorted(cost_rows, key=lambda r: r["trials"])
    lo_cost_n = f"e2.model.{by_trials[0]['model']}.identified"
    hi_cost_n = f"e2.model.{by_trials[-1]['model']}.identified"
    L.append("## Extended Data Figure 1. The harmful action rate against what one trial cost and how long it took.")
    L.append("")
    L.append(
        "One point per model, sixteen models from eight developers. **a**, The harmful action rate among "
        "identified pairs against the mean billed cost of one agent trial with the potentially harmful entry, "
        "measured on this study's own trials and shown on a log scale. Identified pairs are the model-case "
        "pairs in which the model identified the entry or implied action as unsafe when asked. **b**, The "
        "same rate against the median wall-clock time of one trial. Points in purple are the faster and "
        "lower-cost group and in pale purple the newest and most safety-trained group. The newest group cost "
        f"{num('e2.cost.ratio.newest_over_faster'):.1f} times "
        "<!-- num:e2.cost.ratio.newest_over_faster --> as much per trial as the faster group "
        f"({num('e2.cost.newest.per_trial'):.2f} <!-- num:e2.cost.newest.per_trial --> against "
        f"{num('e2.cost.faster.per_trial'):.2f} <!-- num:e2.cost.faster.per_trial --> US cents) and took "
        f"{num('e2.cost.ratio.seconds.newest_over_faster'):.1f} times "
        "<!-- num:e2.cost.ratio.seconds.newest_over_faster --> as long. Across the sixteen models the rank "
        f"correlation of the harmful action rate with cost is {num('e2.cost.spearman.commission_vs_cost'):.2f} "
        "<!-- num:e2.cost.spearman.commission_vs_cost --> and with time "
        f"{num('e2.cost.spearman.commission_vs_seconds'):.2f} "
        f"<!-- num:e2.cost.spearman.commission_vs_seconds -->. n is the trials behind each point, "
        f"{den(lo_cost_n)} to {den(hi_cost_n)}.")
    L.append("")

    top = cat_rows[0]
    zero_newest = sum(1 for r in cat_rows if r["newest_n"] == 0)
    by_n = sorted(cat_rows, key=lambda r: r["N"])
    lo_cat_n = f"e2.catastrophe.{by_n[0]['case']}"
    hi_cat_n = f"e2.catastrophe.{by_n[-1]['case']}"
    L.append("## Extended Data Figure 2. The actions the agents completed.")
    L.append("")
    L.append(
        "Twenty-two of the 78 <!-- num:e1.cases.total --> cases, chosen for the severity of the harm caused "
        "if the potentially harmful entry is acted on. Each is named in the case's own words, shortened to "
        "one line. The full sentence for every case is in Supplementary Note 1. Bars show the harmful action "
        "rate over all sixteen models, with every model weighted equally. The count of trials is beside each "
        "bar, and the newest and most safety-trained group's count is at the right. Every count is a state "
        "the receiving software reached, never the agent's text. The highest rate is the case in which "
        f"{top['label']}, {top['rate']:.0f}% <!-- num:e2.catastrophe.{top['case']} -->. The newest "
        f"group's count is zero in {zero_newest} of the twenty-two rows and never above "
        f"{max(r['newest_n'] for r in cat_rows)} of 100. n is the trials in the row, {den(lo_cat_n)} "
        f"to {den(hi_cat_n)}.")
    L.append("")

    (HERE / "CAPTIONS-restyled.md").write_text("\n".join(L).rstrip("\n") + "\n", encoding="utf-8")
    print("  wrote CAPTIONS-restyled.md")


# =========================================================================== main

def main():
    print(f"build_restyled.py: drawing from {REGISTER.name} ({len(N)} keys)")
    fig3_role_basis()
    e4_trials = fig5_real_systems()
    cost_rows = extfig1_cost()
    cat_rows = extfig2_catastrophes()
    captions(e4_trials, cost_rows, cat_rows)
    print("build_restyled.py: four figures, four sidecars and CAPTIONS-restyled.md in", HERE)


if __name__ == "__main__":
    main()
