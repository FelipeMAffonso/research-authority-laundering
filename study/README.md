# The study package: what it contains and how to reproduce every number

This folder holds the data, code and records of the study. Every number in the manuscript, in the Supplementary
Information and in the figure captions is produced from the files in this folder by the commands below, and the
commands read only this folder, the Python standard library and the packages pinned in `requirements.txt`. The layout
has one folder per experiment, because the four experiments run on different software.

## Reproduce every number

Python 3.12 or later. From this folder:

    python -m pip install -r requirements.txt

    python -X utf8 analysis/robustness_mixed.py   # the trial-level regression checks of Supplementary Note 3 (statsmodels)
    python -X utf8 analysis/analyze.py

`analysis/analyze.py` reads every dataset and writes `analysis/PAPER-NUMBERS.json` and each experiment's
`results.md`. Every number reported in the paper is an entry of `analysis/PAPER-NUMBERS.json`. Given a text in which
each number carries its entry name in an HTML comment, of the form `<!-- num:e2.commission.all.model_weighted -->`,
`verify.py --no-run --manuscript <file>` compares every such number with the analysis at the precision the text
writes it, exits non-zero and names each number that differs; a key the text names that the analysis does not
produce is a failure, not a skip.

`python -X utf8 analysis/verify.py --selftest` shows that the comparison refuses a wrong number: it passes a clean
control, catches a changed value and a changed count, and reports an unknown key.

`analysis/robustness_mixed.py` fits a variational Bayes mixed model, so the last digits of its odds ratios can differ
from one run to the next (in the seventh significant digit); the values the manuscript reports, at two decimals, do
not change.

The figures, after the analysis has run:

    python -X utf8 paper/figures_nature/build_restyled.py         Fig. 4, Fig. 6, Extended Data Figs 1 and 2
    python -X utf8 paper/figures_nature/build_charts.py           Fig. 3, Fig. 5, Extended Data Fig. 3
    python -X utf8 paper/figures_nature/build_fig1_schematic.py   Fig. 1
    python -X utf8 paper/figures_nature/build_fig2_trace.py       Fig. 2
    python -X utf8 paper/figures_nature/build_quotes_cards.py     Extended Data Fig. 4

The last three render HTML in a headless Chrome or Edge through Playwright, looking for the browser where Windows
installs it, and use the Material Symbols icon font in `paper/figures_nature/fonts/`, so no network is needed. Each
figure writes a sidecar JSON beside it naming the analysis keys it read.

Rerunning the experiments themselves, not the analysis, needs API keys and about 400 dollars; each experiment README
says how, and names the shared modules needed to run them again that this folder does not carry.

## The same-trial reading

`experiment-3-assessment-before-acting/same_trial.py` put the sentence the agent stated beside the action it then
took, in the same trial. Every judged trial is in that experiment's `same_trial/` folder, one file each, and
`same_trial.json` and `same_trial_results.md` hold the counts written from those files. To recompute them:

    python -X utf8 experiment-3-assessment-before-acting/same_trial.py --summary --per-stratum 120

It calls no model and reads only the judged trials. Every count of judged statements and actions comes back
identical. Three things do not. The descriptions of the keys and the headers of one table come back in different
wording ("said wrong" where the files say "said unsafe", "the harmful value" where they say "the harmful entry's
value"). Two sentences of `same_trial_results.md` change: the script's screen runs over every case in
`cases/cases.json`, so it reports 84 admitted cases (the bank's 71 and the follow-up study's 13) where the file says
71, and it quotes the knowledge check's rate on admitted cases from the current analysis, 96.5 per cent, where the
file says 96.6. And the size of the pool the sample was drawn from, recorded as 12,304 test-record trials when the
sample was drawn and judged, comes back as 12,120 from the released data. Two cases, the shared-files case and
the card-refund case, had their three assessment cells set aside and only their assess_free cell rerun when those two systems were repaired, so
160 of the 7,607 judged statements are of trials that are no longer rows in
`experiment-3-assessment-before-acting/data/`; the statements and the actions themselves are in `same_trial/`, which
is what every count is read from. No number in the manuscript, the Supplementary Information or a caption uses the
pool size. The command overwrites `same_trial.json` and `same_trial_results.md`, so run it on a copy to keep them as
they are.

## The question

Every case has two versions of the same record. The test record holds one ordinary entry that, used in the requested
task, can produce the harm that case names: the potentially harmful entry. The entry states no instruction to the
agent, and the agent has a basis for rejecting it, which is what a competent person in the role already knows (a
dose, a law, a chemistry rule), a fact the instructions state, or a second record the same lookup returns beside the
case record. The matched control record differs only in that entry, and it supports the legitimate action or the
correct non-action. The question is whether the same model, given the same record, calls the entry unsafe when it is
asked as an assistant and still commits the action when it runs the task as an agent. Cases where the agent has no
basis for rejecting the entry are not part of this study.

Case ids that begin `N_FU_` belong to the follow-up study and are reported apart from the 78-case bank.

## The four experiments

| folder | what it measures | paper section |
|---|---|---|
| `experiment-1-knowledge-check/` | asked as an assistant: does the model say the value is unsafe, and does it also say so about the control record (the leading-question control) | Identification when asked; Methods |
| `experiment-2-agent-task/` | acting as an agent: the harmful action rate, by role (implementing, ordering), by where the basis lives (knowledge, prompt, second record), on the test record and on the control record | Harmful actions when acting; Roles and the basis; Fig. 3 and Fig. 4 |
| `experiment-3-assessment-before-acting/` | the same loop with one added sentence: a safety assessment against a neutral restatement of the record, with and without the clause "then act on your own judgment" (a two-by-two) | Assessment before acting; Fig. 5 |
| `experiment-4-real-systems/` | twenty-nine demonstrations on real software: sixteen written by other teams (physics engines, an astronomy library, a synchrotron beamline model, a liquid handler, a version-control registry, a filesystem, a shell, a cloud emulator, an MCP server, three agent frameworks) and thirteen office and research systems built to their vendors' documentation (mail, calendar, shared files, card and research payments, a gradebook, a compute cluster, an editorial system, a preprint server, a data repository, a code forge, a structure-prediction job service), each running its case with the basis in the prompt and in a second record | The real systems; Fig. 6; Supplementary Note 5 |

Three pieces sit inside those folders and are reported apart:

| where | what it is | paper section |
|---|---|---|
| `experiment-2-agent-task/followup.md` and the `e5.followup.*` keys | the follow-up study: twenty further cases (ids `N_FU_*`) added after the main bank, run in one pass through the knowledge check, the agent task and the assess_free cell, and analyzed with the bank's own rules; no number in the four experiments includes one of their trials, and the analysis refuses if one reaches a bank table | A follow-up study; Methods |
| `experiment-3-assessment-before-acting/same_trial.py`, `same_trial.json`, `same_trial_results.md`, `same_trial/` | what the agent said before acting, scored in the same trial as what it did: an even sample of 7,607 test-record trials from the four cells, the statement judged by the knowledge-check judge, cross-classified against the action | Assessment before acting; Methods |
| `experiment-4-real-systems/outcome_levels.json`, `OUTCOME-AUDIT.md`, `STRIPE-SHARE-REPAIR.md` | the outcome audit: for each of the twenty-nine systems, which program received the action, whether a real state changed, and whether the vendor's live service would execute the same call; the two systems the audit found scoring an action the live service refuses (card refunds, shared files) and their repair as valid but harmful actions | Methods; Supplementary Note 5, Supplementary Table 14 |

Each experiment folder has the same shape:

    README.md        the design in plain English, the exact prompts, how the runner works, how to rerun it
    code/            the runner and the scoring
    data/            the dataset, one JSON Lines file per model (gzip), one row per trial or answer
    results.md       the tables the analysis produced from data/ (generated)

## The rest

    cases/           the case bank: cases.json (every case: family, basis type, system text, request, both records,
                     the second record where there is one, the plain catastrophe), CASE-BANK.md (the readable form),
                     PROMPTS-AS-SENT.md (every prompt exactly as the runs sent it), value_kinds.json (whether each
                     numeric case's value is a quantity or an identifier, which decides how a committed value is
                     matched)
    analysis/        analyze.py produces every number and table in the paper from data/ and writes
                     PAPER-NUMBERS.json; verify.py compares every marked number in a text with it;
                     robustness_mixed.py writes the trial-level regression checks
    paper/           figstyle.py, figures.py and figures_nature/ with the ten figures, their sidecars and their
                     builders
    audit/           the files the Supplementary Information quotes: the design written down before anything ran
                     (REDO-DESIGN.md) with its dated amendments, the judge agreement (JUDGE-AGREEMENT.md), the cells
                     of the earlier experiments that had no basis (ARCHIVE.md), the rates by class (BASIS-RATES.md),
                     the list of cases run again after their text was corrected (RERUN-AFTER-FIX.md) and the two bank patches

## Naming

The experiments are numbered by the order the paper reports them and named by what they measure. Inside the data,
a trial's `experiment` field holds that name. Scenario ids in `experiment-2` read `<case>__<role>__<basis>`;
in `experiment-3` they add the cell: `__assess`, `__assess_free`, `__neutral`, `__neutral_free` (free means the
clause "then act on your own judgment" is present). The data dictionary in each README lists every field.

The rows use the package's names: a row's `variant` is `test` for the test record and `control` for the matched
control record, and in experiments 1 and 4 the same distinction is the `arm` field. One field keeps the name the run
wrote: `_file`, the name of the raw deposit file the row came from; the same-trial register keys its judged trials by
that name, so renaming it would leave each judged statement without its trial.

Two words in the results files that analyze.py writes are the paper's terms under other names: commission is the harmful action
rate (the committed value matching the case's predefined harmful action value), and the free cells of experiment 3
are the cells with the clause "then act on your own judgment". Names of the form `demo_<system>` are the names the
runs used for the `<system>/` folders of experiment-4-real-systems. In experiment 4 the basis placement is the folder
and field `P` (the fact in the system text) or `R` (the fact returned as a second record), the prompt and
second-record placements of the paper.

## Size

The package is about 36 MB, most of it the judged statements of the same-trial reading and the gzipped datasets.
