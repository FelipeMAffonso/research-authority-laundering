# Figure style for the paper, taken from the Nature benchmark

Set on 9 September 2026: white ground, one purple, no layers of titles, no cartoon robots, no meta commentary, consistent across every figure. The benchmark is a set of published Nature figures (Köbis et al. 2025 Fig. 1 and Fig. 2; Betley et al. 2026 Fig. 1 and Fig. 2; CAIS 2026 Fig. 1 and Fig. 2). Every builder imports `study/paper/figstyle.py` and uses nothing outside it for colour, type or size.

## What the benchmark figures have in common

- Pure white ground. No panel background, no shaded band, no coloured frame.
- Nothing inside the figure except the content, the panel letters (bold lower-case a, b, c), the axis labels, the tick labels, the value labels and a one-row legend without a frame. No figure title, no panel title, no subtitle, no footnote, no note. The caption carries the title and every method note.
- One or two hues with their tints (Köbis: a dusty red and a pale blue; Betley: three marker colours), plus grey and black. Ours: purple `#5B54D6`, its tint `#C9C6F1`, grey `#8C8C8C`, its tint `#DADADA`, red `#C8453A` for harm only, ink `#1A1A1A`. The same six in every figure, main and Extended Data. No textures, no hatching, no second purple.
- Small regular-weight type: 7 pt labels, 6.5 pt ticks, 7 pt value labels, 8 pt bold panel letters, at the final printed width (88 mm single column, 180 mm double). Arial. Numbers on bars are regular weight, never large bold headlines.
- Thin whiskers (0.6 pt) with small caps; top and right spines off; no grid.
- Schematics (Köbis Fig. 1, Betley Fig. 1) are flat: a grid of boxes with small grey column headers, short text inside pale boxes, thin arrows, simple line icons. No isometric scenes, no characters at desks, no dome.
- Captions: `Fig. N | ` then a plain descriptive title (a full sentence or a descriptive noun phrase, never a fragment or a slogan), then `a, ...` and `b, ...` in plain words, then what bars, whiskers and n are. Nothing about files, keys, registers, sidecars, builders or how the number was read.

## The nine figures, rebuilt to this spec

All nine come out of one folder, `study/paper/figures_nature/`, at 300 dpi PNG plus PDF, with one shared style module, so they cannot differ in ground, palette or type.

1. Figure 1, the study in one schematic (180 mm). Four columns under small grey headers: the task and record (the request in a pale grey box; the record as five short lines with the wrong line in red); the lookup (the record returned through the tool, and the model's answer when asked, verbatim, in a pale purple box); the action (the tool call in monospace in a pale box, the value in red); the receiving system (its recorded state in one line, and the rate in plain text: "completed the action in 22 per cent of trials, 69 of 315"). Beneath, three rows for three other cases in the same four columns, shortened. The agent is a small robot (the author's ruling), one clean flat glyph in ink outline with a purple-tint fill, in the manner of the robot in Anthropic's Figure 1 (boxy head, two dot eyes, a simple body, a short antenna), drawn once and reused in each column at no more than 12 mm tall: reading the record, answering when asked, calling the tool, the call reaching the switch. Other icons are simple line icons in ink (a document, a magnifier, a switch, a building). No desk scene, no monitor, no dome, no isometric room.
2. Figure 2 (180 mm): three panels a, b, c, two bars each (purple asked, grey acting), value labels, whiskers on the acting bars.
3. Figure 3 (180 mm): the roles and the three homes of the fact, as now, restyled.
4. Figure 4 (180 mm): a, the statement before the tool call (purple did not act, red completed the action, grey the knowledge check); b, the harmful action rate by sentence (purple, with the no-sentence baseline in grey). One legend row for the whole figure.
5. Figure 5 (180 mm): the real systems, as now, restyled: purple for the fact in the instructions, purple tint for the fact in a second record, grey for the accurate-record job.
6. Extended Data Fig. 1 (88 or 180 mm): the harmful action rate against cost per trial, restyled.
7. Extended Data Fig. 2 (180 mm): the actions completed, all twenty-two, restyled.
8. Extended Data Fig. 3 (180 mm): the sixteen models. Purple bars for the faster group, purple tint for the newest, grey hollow circles for identification. No textures, no developer colours; the developer is in the tick label ("Gemini 3.0 Flash (Google)").
9. Extended Data Fig. 4 (180 mm): the six verbatim statements and their tool calls, as flat text boxes on white with a thin rule between cards; the statement in ink with the key phrase bold; the tool call in monospace in a pale grey box. No robot icon.

## What every builder must do

- `import figstyle` and call `figstyle.figure`, `figstyle.clean`, `figstyle.panel_label`, `figstyle.whisker_kw`, `figstyle.value_label`, `figstyle.legend_row`, `figstyle.save`. No `ax.set_title`, no `fig.suptitle`, no `fig.text` notes, no `ax.set_facecolor` other than white, no colours outside the six.
- Read every number from `study/analysis/PAPER-NUMBERS.json` by key and record the keys in a sidecar JSON next to the PNG (the sidecar records where each number came from; it is never mentioned in a caption).
- Write the caption for the figure into `study/paper/figures_nature/CAPTIONS.md` under `## Figure N. Title` or `## Extended Data Figure N. Title`, in the caption form above, with the numbers that appear in the caption carrying their `<!-- num:key -->` marker. No preamble in that file, nothing before the first heading.
- Open the PNG and look at it before using it.
