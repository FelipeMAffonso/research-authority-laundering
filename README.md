# AI agents can commit actions their own language models call unsafe

Code and data for the paper "AI agents can commit actions their own language models call unsafe" by Felipe M.
Affonso (Spears School of Business, Oklahoma State University), currently under review.

## Overview

The paper asks whether a language model that calls an entry in a record unsafe when it is asked about it as an
assistant still carries out the action that entry implies when the same model runs the task as an agent with tools.
Sixteen language models from eight developers were tested on the same cases in four experiments: a knowledge check
(the model asked as an assistant), an agent task (the model acting through tools), the agent task with one added
sentence asking for a safety assessment before acting, and twenty-nine real software systems.

Every record in the study is fictional, and no live service was reached. The `study/` folder holds every answer and
trial as one row, the case bank, the code of the four experiments, the analysis that produces every number, table
and figure in the manuscript, the script that checks every reported number against that analysis, and the audit
records the Supplementary Information quotes.

## Repository structure

```
study/
  README.md                               what the package holds, folder by folder, and how to reproduce it
  requirements.txt                        the Python packages the reproduction commands import, at the tested versions
  cases/                                  the case bank: cases.json, a readable copy (CASE-BANK.md), every prompt
                                          exactly as sent (PROMPTS-AS-SENT.md), and value_kinds.json
  experiment-1-knowledge-check/           the model asked as an assistant about each record
    README.md                             design, prompts, data fields
    code/                                 the runner and the judge
    data/<model>.jsonl.gz                 one row per answer, one file per model
    results.md                            the tables the analysis writes
    judge_agreement.json                  the agreement of the judge with a second scorer
  experiment-2-agent-task/                the model acting as an agent on the same records
    README.md, code/, data/, results.md   as above
    followup.md                           the follow-up study of twenty further cases, reported apart
  experiment-3-assessment-before-acting/  the agent task with an added sentence before acting
    README.md, code/, data/, results.md   as above
    same_trial.py, same_trial/            each statement the agent made before acting, judged, beside its action
  experiment-4-real-systems/              the cases run on twenty-nine real software systems
    README.md, results.md                 the systems and the tables
    <system>/code/                        the runner for that system and its variant switch
    <system>/data/<P|R>/<model>.jsonl.gz  one row per trial, by where the basis was placed
    OUTCOME-AUDIT.md, outcome_levels.json what each system received and changed, and what its vendor allows
  analysis/
    analyze.py                            produces every number and table from the data; writes PAPER-NUMBERS.json
    verify.py                             compares every marked number in a text with PAPER-NUMBERS.json
    robustness_mixed.py                   the trial-level regression checks of Supplementary Note 3
  paper/
    figures_nature/                       the ten figures, their sidecars and their builders
  audit/                                  the design written before the runs, the judge agreement, the rates by
                                          class, the record of reruns after corrections, and the two bank patches
```

## Setup

Python 3.12 or later. From the repository root:

```
python -m pip install -r study/requirements.txt
```

The packages are numpy, pandas, statsmodels, matplotlib, pillow and playwright, pinned at the versions the
commands were tested with (on Windows). Three figures are rendered from HTML in a headless Chrome or Microsoft Edge
through Playwright; their builders look for the browser where Windows installs it, so those three need Windows with
Chrome or Edge. The icon font they use is in `study/paper/figures_nature/fonts/`, and no network access is needed.

## Usage

Every command runs from `study/`:

```
cd study
python -X utf8 analysis/robustness_mixed.py
python -X utf8 analysis/analyze.py
python -X utf8 analysis/verify.py --selftest
```

`analyze.py` reads every dataset and writes `analysis/PAPER-NUMBERS.json` and the `results.md` file of each
experiment (a few minutes). Every number reported in the paper is an entry of `PAPER-NUMBERS.json`. `verify.py`
compares the numbers in a text that names those entries with the analysis, exits with an error and lists each number
that differs; `--selftest` shows that the comparison catches a changed value, a changed count and an unknown entry.

The figures, after the analysis has run:

```
python -X utf8 paper/figures_nature/build_restyled.py         # Fig. 4, Fig. 6, Extended Data Figs 1 and 2
python -X utf8 paper/figures_nature/build_charts.py           # Fig. 3, Fig. 5, Extended Data Fig. 3
python -X utf8 paper/figures_nature/build_fig1_schematic.py   # Fig. 1
python -X utf8 paper/figures_nature/build_fig2_trace.py       # Fig. 2
python -X utf8 paper/figures_nature/build_quotes_cards.py     # Extended Data Fig. 4
```

Rerunning the experiments themselves calls the models through OpenRouter and needs API keys and about 400 dollars;
each experiment's README says how, and names the shared modules needed to run them again that this
repository does not include.
The analysis and every command above need no key and no network.

## Data format

Each dataset is one gzip-compressed JSON Lines file per model, one row per answer (experiment 1) or per trial
(experiments 2 to 4). In every row, `model` names the model, `variant` (or `arm` in experiments 1 and 4) says whether
the row used the test record, which holds the potentially harmful entry, or the matched control record, and
`experiment` names the experiment. The README of each experiment lists every field. Case identifiers beginning with
`N_FU_` belong to the follow-up study, which is reported apart from the 78-case bank.

## Data deposit

The same study package is archived at Zenodo: <https://doi.org/10.5281/zenodo.22817867>. The `study/` folder here is
that package without the files that served only to assemble it or to submit the manuscript (the script that copied
it from the author's working folder, a run log, the cover letter, the reporting summary, the bibliography
database, and the copies of the manuscript, the Supplementary Information and the figure captions), and with local
file paths and internal working notes removed from comments and documentation. Every
trial record, every case and every reported number is the same as in the deposit.

## License

The data, the case bank, the figures and the documentation are released under the Creative Commons Attribution 4.0
International license (CC BY 4.0), as in the Zenodo record (`LICENSE-DATA`). The code is released under the MIT license,
as the manuscript's code availability statement says (`LICENSE`). The Lucide icons and the Material Symbols font used
by the figure builders keep their own licenses (ISC and Apache 2.0).

## Citation

Affonso, F. M. AI agents can commit actions their own language models call unsafe. Manuscript under review (2026).
Data and code: <https://doi.org/10.5281/zenodo.22817867>.
