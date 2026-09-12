---
name: run-and-triage
description: Use when running the Tumor Evaluation Review Agent on a data cut, reading its coverage report or rule activation profile, investigating why it produced too many or too few findings, or preparing output for CDM and Medical Monitor review. Covers APPLY slot A-10. Trigger on mentions of running the agent, a data cut, the coverage report, deactivated rules, false positives, finding volume, or "why did the agent flag this".
---

# Running TEA and triaging its output

You are running the agent and producing APPLY slot **A-10** (the rule activation
profile for this study and this cut). The activation profile is *generated*, not
authored — your job is to read it, explain it, and get it accepted.

## Always run deterministic-only first

Mode B — no model at all. Full rule coverage, template narratives, confidence
from the rule base rate alone.

Do this on every new study and after every conversion change, before any run
that involves GLM. It separates conversion defects from model behaviour. If the
first real run is model-assisted and the output is wrong, you cannot tell which
half is at fault, and you will spend a day finding out.

## Read the coverage report before the worklist

Every run states which rules were active, which were deactivated, and what
missing input deactivated each one.

**A quiet worklist is not good news until you have read this.** Under SDTM,
more rules are conditional than under a direct EDC extract — a thin delivery
produces a short finding list that looks like clean data. The coverage report is
what distinguishes "the study is in good shape" from "we checked a third of what
we meant to check."

Take the activation profile to the study team and have them accept it
explicitly. Their acceptance is what makes the run's scope a decision rather
than an accident.

## Triaging volume

**Too many findings.** In order of likelihood:

1. `non_evaluable_rules` not configured — every gap becomes a finding. This is
   the largest single source of avoidable volume.
2. The protocol/charter conflict left a threshold at a guideline default that
   the study does not use.
3. Reader streams merged in conversion — `TUEVAL`/`RSEVAL` not separated, so
   every lesion duplicates and two readers doing their job reads as a
   discrepancy.
4. Query history missing or unmapped, so nothing is suppressed as
   `DUPLICATE_OPEN` and the agent re-raises what the study team already asked.
5. Measurement rounding tolerance unset (`measurement_precision`), surfacing
   rounding differences as low-confidence findings.
6. Cascade grouping not doing its job — one root cause should produce one
   finding with consequences attached, not one finding per affected visit.

**Too few findings.** More dangerous, and check these first:

1. Rules deactivated for missing inputs — read the coverage report.
2. Over-suppression by query reconciliation, usually because lesion-level
   matching fell back to visit level when the item-group sequence was lost. Look
   at the suppressed-findings view, not just the worklist.
3. The conversion recomputed a derived value, so the agent is comparing its
   derivation against its own arithmetic and every discrepancy vanished.
4. Baseline misidentified — `EPOCH` not populated — so percentages are computed
   from the wrong reference.

Note that trap 3 and trap 4 both produce *plausible, clean* output. Neither
announces itself.

## Before findings go to a reviewer

- Confirm the run provenance is complete: rule pack version, prompt versions,
  model version, protocol and charter content hashes, conversion version, query
  file as-of date and SHA-256.
- Confirm the query file's as-of date is within tolerance of the SDTM cut. A
  stale query file manufactures false `NEW` findings.
- Check the suppressed-findings view. Suppression is never silent by design;
  make sure someone looks at it.
- Sanity-check a handful of findings by hand against the source. Not to approve
  them — to confirm the pipeline is pointing at the data you think it is.

## What you may and may not do with output

You may explain a finding, group findings, summarise volume, and identify
patterns worth the study team's attention.

You may **not** dismiss a finding, change its severity, change its confidence
rate, or decide it is a false positive. Adjudication is a human act recorded
against a named person (AC-10). Your read of a finding is an opinion; only the
reviewer's disposition is a decision.

If you believe a rule is generating false positives systematically, that is a
change request against the rule pack — see `common-change-request`. It is not
something to filter out locally.

## Done when

- A deterministic-only run completes end to end.
- The activation profile is accepted by the study team and attached to the run.
- The coverage report has been read and its deactivations explained.
- Provenance is complete and the query file is within cut tolerance.

## Stop and ask when

- The activation profile shows a family largely deactivated — that is a
  conversion or configuration gap, not a normal run.
- Finding volume changes sharply between cuts with no corresponding data change.
- Any finding appears against a subject or visit that should not be in scope.
