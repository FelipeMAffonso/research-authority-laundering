"""The spec-resistance companion site's robot, with its faces.

The drawing is the companion's own (github.com/FelipeMAffonso/spec-resistance-companion, SVG symbols
bot-ai, bot-ai-thinking, bot-ai-confab, bot-ai-honest, bot-ai-stubborn, copied from the live page on
2026-09-10). The body is the same in every variant; the mouth and the two colours differ. robot(face,
body, antenna) returns the inner SVG for a 120 x 140 viewBox; sheet() draws every variant with its name.

    python -X utf8 robot_faces.py    writes robot-faces.png beside this file
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

GREY_BODY, CORAL = "#BFC3C7", "#DA7756"          # bot-ai
GREEN_BODY, GREEN = "#A8CFA0", "#3F7A5A"          # bot-ai-confab
BLUE_BODY, BLUE = "#9CC2DC", "#3A6FB0"            # bot-ai-honest
ORANGE_BODY, ORANGE = "#E69A85", "#B85F40"        # bot-ai-stubborn

MOUTHS = {
    "neutral":  ('<rect x="44" y="62" width="32" height="10" rx="2" fill="#fff" stroke="#1c1c1c" stroke-width="1.4"/>'
                 '<line x1="52" y1="62" x2="52" y2="72" stroke="#1c1c1c" stroke-width="1.2"/>'
                 '<line x1="60" y1="62" x2="60" y2="72" stroke="#1c1c1c" stroke-width="1.2"/>'
                 '<line x1="68" y1="62" x2="68" y2="72" stroke="#1c1c1c" stroke-width="1.2"/>'),
    "thinking": ('<circle cx="60" cy="68" r="4" fill="none" stroke="#1c1c1c" stroke-width="1.8"/>'
                 '<circle cx="60" cy="74" r="0.8" fill="#1c1c1c"/>'),
    "confab":   '<path d="M 48 68 Q 56 64 60 67 Q 64 70 72 65" fill="none" stroke="#1c1c1c" stroke-width="2" stroke-linecap="round"/>',
    "honest":   '<path d="M 48 65 Q 60 73 72 65" fill="none" stroke="#1c1c1c" stroke-width="2" stroke-linecap="round"/>',
    "stubborn": '<path d="M 48 71 Q 60 63 72 71" fill="none" stroke="#1c1c1c" stroke-width="2" stroke-linecap="round"/>',
}

# the companion's own pairing of face and colour
COMPANION = {
    "bot-ai": ("neutral", GREY_BODY, CORAL),
    "bot-ai-thinking": ("thinking", GREY_BODY, CORAL),
    "bot-ai-confab": ("confab", GREEN_BODY, GREEN),
    "bot-ai-honest": ("honest", BLUE_BODY, BLUE),
    "bot-ai-stubborn": ("stubborn", ORANGE_BODY, ORANGE),
}


def robot(face: str = "neutral", body: str = GREY_BODY, antenna: str = CORAL) -> str:
    """Inner SVG of the robot with the named face, for a viewBox of 0 0 120 140."""
    return (f'<line x1="60" y1="6" x2="60" y2="22" stroke="#3a3a3a" stroke-width="2.4" stroke-linecap="round"/>'
            f'<circle cx="60" cy="6" r="3.8" fill="{antenna}"/>'
            f'<rect x="24" y="22" width="72" height="58" rx="12" ry="12" fill="{body}" stroke="#1c1c1c" stroke-width="2.2"/>'
            '<rect x="14" y="40" width="12" height="22" rx="3" fill="#C94C3A"/><rect x="94" y="40" width="12" height="22" rx="3" fill="#C94C3A"/>'
            '<circle cx="46" cy="46" r="8" fill="#fff" stroke="#1c1c1c" stroke-width="1.6"/><circle cx="74" cy="46" r="8" fill="#fff" stroke="#1c1c1c" stroke-width="1.6"/>'
            '<circle cx="46" cy="46" r="3" fill="#101010"/><circle cx="74" cy="46" r="3" fill="#101010"/>'
            + MOUTHS[face] +
            f'<rect x="54" y="80" width="12" height="8" fill="#7A7F84"/>'
            f'<rect x="20" y="88" width="80" height="28" rx="6" fill="{body}" stroke="#1c1c1c" stroke-width="2.2"/>'
            '<rect x="50" y="94" width="20" height="16" rx="3" fill="#F4F1EC" stroke="#1c1c1c" stroke-width="1.4"/>'
            '<line x1="55" y1="99" x2="65" y2="99" stroke="#1c1c1c" stroke-width="1.2"/><line x1="55" y1="103" x2="65" y2="103" stroke="#1c1c1c" stroke-width="1.2"/>')


def svg(face: str = "neutral", body: str = GREY_BODY, antenna: str = CORAL, size: int = 62) -> str:
    return f'<svg viewBox="0 0 120 140" width="{size}" height="{round(size * 140 / 120)}">{robot(face, body, antenna)}</svg>'


def sheet() -> str:
    """Every companion variant on the first row; every face on the grey body on the second."""
    cell = ('<div style="text-align:center;width:150px"><svg viewBox="0 0 120 140" width="110" height="128">{r}</svg>'
            '<div style="font:12px Arial;color:#1A1A1A;margin-top:4px">{name}</div><div style="font:11px Arial;color:#8C8C8C">{note}</div></div>')
    row1 = "".join(cell.format(r=robot(f, b, a), name=k, note=f"{f} face, body {b}") for k, (f, b, a) in COMPANION.items())
    row2 = "".join(cell.format(r=robot(f), name=f"{f} face", note="grey body, coral antenna") for f in MOUTHS)
    return ('<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#fff;width:1063px;padding:16px 24px;box-sizing:border-box">'
            '<div style="font:700 13px Arial;margin:0 0 10px">The companion site\'s robots, as it draws them</div>'
            f'<div style="display:flex;gap:18px;flex-wrap:wrap">{row1}</div>'
            '<div style="font:700 13px Arial;margin:22px 0 10px">The same body with each face, for one model in two arrangements</div>'
            f'<div style="display:flex;gap:18px;flex-wrap:wrap">{row2}</div></body></html>')


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    from build_fig1_cards import find_chrome
    from playwright.sync_api import sync_playwright
    html_path = HERE / "robot-faces.html"
    html_path.write_text(sheet(), encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=find_chrome(), headless=True)
        pg = b.new_page(viewport={"width": 1063, "height": 200}, device_scale_factor=2)
        pg.goto(html_path.as_uri()); pg.wait_for_timeout(300)
        pg.screenshot(path=str(HERE / "robot-faces.png"), full_page=True)
        b.close()
    print(HERE / "robot-faces.png")
