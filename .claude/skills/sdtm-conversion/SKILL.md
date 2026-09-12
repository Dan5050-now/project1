---
name: sdtm-conversion
description: Use when converting Veeva EDC raw data to SDTM for the Tumor Evaluation Review Agent, writing or reviewing an SDTM conversion specification, mapping CRF items to TU/TR/RS or the cross-domain set, or diagnosing why the agent reports missing or wrong tumour data. Covers APPLY slots A-01 (conversion specification) and A-02 (conversion code). Trigger on mentions of SDTM, TU, TR, RS, TULNKID, define.xml, CRF mapping, or "convert the EDC data".
---

# SDTM conversion for TEA

You are producing APPLY slots **A-01** (the conversion specification) and
**A-02** (the conversion code). The requirement you are satisfying is
**TEA-CTR-003**, on sheet `SDTM_Requirements` of the programming specification.
Read that sheet first — every variable, whether it is required, and what breaks
without it.

## The rule that governs this task

**You write the conversion. You do not perform it by judgement.**

Produce deterministic code that a human reviews and qualifies. Never emit
converted data values yourself — not as a sample, not as a fixture, not "to
show the shape", not for the tricky records the code does not handle yet. A
model that generates SDTM values sits upstream of every deterministic verdict
the agent makes, and no check downstream can detect it. This is DP-01 and law
L3; it is the reason the agent can claim a model cannot change a finding.

If a record cannot be converted by rule, it is an unconverted record and it is
reported. It is never converted by inference.

## Before you start

You need **K-03** (the Veeva EDC build: CRF specification, item OIDs,
codelists, and the repeating-group structure) and **K-05** (SDTM IG version,
sponsor conventions, controlled terminology release). Without the
repeating-group structure you cannot do lesion identity or query matching. If
it is missing, stop and ask for it.

## The six failure modes

These are the ones that actually happen, in order of how much damage they do.

**1. Recomputing derived values during conversion.**
If the EDC collected a sum of diameters or a reported response, carry it across
unchanged. Never recalculate it to make it consistent. The agent's entire
purpose is comparing its own derivation against what the site reported — if the
conversion recomputes either side, the agent compares itself with itself and
every real discrepancy silently disappears. This is the single most destructive
thing you can do here, and it looks like helpfulness.

**2. Assigning TULNKID per visit instead of per lesion.**
`TULNKID` is the lesion's permanent identity, assigned once when the lesion is
first identified and never reused. If it is regenerated at each visit, lesion
history collapses, `TRLNKID` joins nothing, and the 60-plus lesion-level rules
produce nonsense. Verify by checking that a lesion's id is stable across all its
timepoints.

**3. Merging investigator and central review into one stream.**
`TUEVAL` and `RSEVAL` separate them. Merged, every lesion and every response
duplicates, and the agent reports discrepancies that are two readers doing their
job. This produces wrong answers rather than absent ones, which is worse.

**4. Dropping the original unit after standardising to millimetres.**
`TRSTRESN`/`TRSTRESU` standardised to mm, **and** `TRORRES`/`TRORRESU` retained
as collected. The original unit is what lets TE-ST-004 catch a centimetre value
entered in a millimetre field.

**5. Measuring nodes as longest diameter.**
`TRTESTCD` is `SAXIS` for nodal lesions, `LDIAM` for non-nodal, plus `TUMSTATE`
for lesion state. A node carried as `LDIAM` silently breaks every nodal
threshold. If the EDC does not collect the axis type, resolve it from lesion
type per the imaging charter — see TE-ST-003 and `Charter_Requirements`.

**6. Using scheduled visit dates instead of actual assessment dates.**
The agent orders timepoints by `--DTC` and dates progression from it. A
scheduled date shifts a progression date, which is a regulatory-grade error.

## Also required, and easy to miss

- **`TUMSTATE`** carried as `TRTESTCD=TUMSTATE` with `TRSTRESC` in
  `PRESENT`/`ABSENT`/`TOO SMALL TO MEASURE`. Without it, a lesion that
  disappeared and one never measured look identical, and complete response
  cannot be confirmed.
- **`TRSTAT = NOT DONE`** where a planned measurement was not taken. A missing
  row is not the same as a not-done row; the agent must be able to tell a
  genuine omission from an intended absence.
- **`RSCAT`** separating RECIST 1.1 from iRECIST whenever both are collected.
  Without it the two response sets are indistinguishable and the agent may
  compare an iRECIST response against RECIST logic.
- **`EPOCH`** populated, so baseline is identified structurally rather than by a
  date heuristic.
- **The EDC item-group sequence**, carried in `SUPPTU` alongside `TULNKID`.
  A Veeva query identifies a lesion *only* by the repeating form's Item Group
  Sequence Number — nothing else in the query export names a lesion. Lose it and
  every lesion query at a visit suppresses every lesion finding at that visit.
  See `Query_History` finding 1.
- **Partial dates stay partial.** Do not impute. Rules that need full precision
  declare it and deactivate cleanly.
- **Unscheduled visits** keep a `VISITNUM` that does not reorder the scheduled
  sequence, and remain identifiable as unscheduled.

## Procedure

1. Read `SDTM_Requirements` in full. Note every **R** variable — those are the
   ones whose absence stops the run.
2. Inventory the EDC build: every form, item group and item that carries tumour
   or cross-domain data. Identify which item group repeats per lesion.
3. Write the specification (A-01): source item → SDTM domain and variable, the
   derivation for each standardised variable, and the controlled terminology
   used. Every **R** variable needs a documented source. Every **C** variable is
   either mapped or explicitly declared unavailable *with the consequence from
   the "If absent" column stated*.
4. Have it reviewed before writing code. A mapping error found here costs
   minutes; found after conversion it costs a re-run and an investigation.
5. Write the code (A-02) with unit tests over each mapping rule, plus a
   reconciliation report against source record counts.
6. Run the conformance check. No unmapped **R** variable.
7. Produce the implied rule activation profile (A-10) and have the study team
   accept it before any finding is reviewed.

## Done when

- No unmapped required variable.
- Reconciliation against source record counts balances.
- The same input produces byte-identical output on a re-run.
- Lesion ids are stable across timepoints for every subject.
- A qualification record exists naming the code version and the specification
  version it implements.

## Stop and ask when

- The repeating-group structure cannot be determined from K-03.
- The EDC does not collect lesion axis type and the charter does not resolve it.
- The item-group sequence cannot be carried through to `SUPPTU` — that is an
  accepted-consequence decision for the study team, not a workaround for you.
- A source item has no clean SDTM home and you are tempted to invent a
  supplemental qualifier. Propose it; do not just create it.
