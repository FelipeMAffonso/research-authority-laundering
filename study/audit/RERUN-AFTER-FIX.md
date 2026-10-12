# Rerun after the bank corrections (2026-09-07 late evening and 2026-09-08)

Cases whose text sent to models changed after the runs started. Their deposits hold the old text and are set aside
(results/*_superseded, never deleted) and rerun. Nothing else is rerun.

## First round (done 2026-09-07: purged, all runs relaunched on the corrected bank)

Full purge (knowledge check and every agent cell):
- N_LAB_COLUMN, N_OPS_ONLYCOPY, N_OPS_REGISTRY, N_VEH_BEAMLINE (the plate case now states the empty column in one line;
  a second line that restated the fact inside the record was removed from the other three)
- N_VEH_TELESCOPE (record fix, and the second record now states the pointing limit)
- N_LAW_IVORY, N_PAY_BRIBE, N_DATA_MINORS, N_OPS_BACKUPS, N_SEC_TLS, N_SEC_AUTH, N_LAB_ACID, N_LAB_BLEACH (reasons in
  _patch_bank_2026_09_08.py)

Partial purge (the second-record placement's agent trials only): N_PPL_CONSENT, second record (the second record now states the rule).

## Second round (2026-09-08, from reading the control-record answers of the excluded cases)

Four more cases changed in the sent text (reasons in _patch_bank_2026_09_08b.py): N_EVD_CAR, N_EVD_PACKAGE,
N_LAB_BLEACH, N_OFF_REPOSITORY_PUBLISH. Purge and rerun them ONLY after the mechanism run (run_new.py --mech only) has
exited, because that process imported the old bank and would refill the cells with the old text. The purge and relaunch
scripts that did this are not part of this package.

demo_repository's panel ran after the fix (its deposits carry the corrected text); its one old-text proof deposit
(results_R/gemini-3.8-flash__FALSE__t0.json) was set aside on 2026-09-08 under results_R/_superseded_2026-09-08.
After the office driver finishes, refill it with:

    python -X utf8 demo_repository/sim.py --run --variant R --workers 2 --reps 5 --true-reps 3
