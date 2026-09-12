---
name: edc-mapping
description: Use when mapping Veeva EDC identifiers for the Tumor Evaluation Review Agent — item OIDs to canonical evidence fields, EDC event labels to SDTM visits, subject identifiers to USUBJID, or configuring query write-back so TEA recognises its own queries. Also use when query reconciliation over-suppresses or under-matches findings. Covers APPLY slots A-04, A-05, A-06 and A-13. Trigger on mentions of Item OID, item group sequence, visit map, USUBJID mapping, query reconciliation, DUPLICATE_OPEN, or the Veeva query export.
---

# EDC mapping for TEA

You are producing APPLY slots **A-04** (field map), **A-05** (visit map),
**A-06** (subject identifier map) and optionally **A-13** (query write-back).
The contract is **TEA-CTR-004**, on sheet `Query_History` of the programming
specification — read it first. It maps all 54 columns of a real Veeva Query
Detail export.

These maps are what let a finding be matched to a query that already covers it.
Get them wrong and the agent either re-raises what the study team already asked
(under-matching — noisy but visible) or suppresses real findings because an
unrelated query looked like a match (over-matching — quiet and dangerous).

## Match keys, in order

A finding matches a query on: **subject → visit → form → item group sequence →
item OID**. Each map you produce supplies one of those links.

## The lesion problem

**Nothing in the Veeva query export identifies a lesion.** For a repeating
tumour form, the Item Group Sequence Number is the *only* thing that says which
lesion row a query sits on.

This has two consequences you must handle:

1. The SDTM conversion must carry that sequence through to `SUPPTU` alongside
   `TULNKID` (see the `sdtm-conversion` skill). If it does not, lesion-level
   matching is impossible.
2. Without it, every lesion query at a visit matches every lesion finding at
   that visit. That is mass false suppression — the worst output the agent can
   produce, and it looks like a clean data set.

If the sequence cannot be carried, do not proceed as if it can. Raise it as an
accepted-consequence decision for the study team.

## Adapter rules you must honour

The company's EDC will change with future Veeva releases. TEA-CTR-004 is built
for that:

- **Bind by column name, never by position.** Column order is not part of the
  contract.
- **Match headers leniently** (trim, collapse spaces, ignore case); **match
  values strictly**.
- **Ignore unknown columns and log them.** A new EDC version adding columns must
  not break a validated run — but the log entry is how anyone notices there is
  new information available.
- **Fail the run on a missing required column**, naming it, before any rule
  executes. A partial reconciliation is more dangerous than none.
- **Fail on an unrecognised value** in `Query Status`, `Manual Query`,
  `Restricted Query`, `Item Value Changed` or `Query Caused Data Change`. These
  vocabularies are small and stable; a new value is a specification event, not
  something to guess at.
- **Empty is unknown, not false.** A blank Yes/No cell must never become `False`.
- **Never parse the filename.** In the sample export the filename says
  `A001-1001` and the `Study` column says `A101-1001_TST5`. The columns are the
  contract.

## Traps in the real export

**`Latest Query Comment` is not the site's answer.** On 64 of 69 rows in the
sample it is a verbatim copy of the query text, and blank on every closed row.
It is the newest message on the thread — for a system query, the query itself.
Passing it to `P-ASSESS-ANSWER` has the model assessing the agent's own query.
The answer is `Latest Query Answer Text`, and only that.

**`Days Unresolved` is measured against the export's listing date**, not the
data cut. Recompute aging from `Query Created Date` against the run's as-of
date. The column is deliberately unmapped.

**`Item Value Changed` and `Query Caused Data Change` are deterministic.** They
answer "was the data corrected, because of this query?" as fact. Under DP-01
that must win over model judgement — read it, do not infer it. A query closed by
`System` with a caused data change is an auto-close on correction, not a
site-accepted resolution.

**The export carries personal data.** `Item Value Before Query` and `Item Value
Now` hold raw field values — in the sample, birth years. Guardrail G-06 redacts
them before any prompt is assembled. `Restricted Query = No` is not assurance;
treat the whole file at clinical-data sensitivity.

## Visit map (A-05)

EDC event label and sequence → SDTM `VISIT`, `VISITNUM`, `EPOCH`.

- Ordering by date and ordering by `VISITNUM` must agree for scheduled visits.
- Unscheduled visits must stay identifiable and must not reorder the sequence —
  the assessment-window rules need to know which visits were scheduled.
- Repeating cycles need `Event Group Sequence Number`. Without it, cycles
  collapse and a query on cycle 2 suppresses a finding on cycle 5. This is the
  most likely silent failure in the contract.

## Subject map (A-06)

EDC `Subject` → `USUBJID`. One-to-one, documented, reversible, and recorded in
the run provenance. The same identifier must resolve across SDTM, the query
export and the application.

## Query write-back (A-13, optional)

If accepted findings are loaded into Veeva as queries, TEA writes its `TE-` rule
id into the `Query Rule` column. That is how the next data cut recognises a
query as its own rather than treating the finding as new.

Test the round trip: TEA raises a query, it appears in the next export, and the
agent matches it to the originating finding.

## Done when

- Every item OID appearing in the query export is mapped, or listed as unmapped
  — never silently dropped.
- A replay of a real export against a real data cut produces the expected
  reconciliation outcome for a reviewed sample, **including at least one
  lesion-level query**.
- Derived timepoint order matches the clinical sequence for a sample including
  at least one subject with an unscheduled assessment.
- No unmatched subject in a full data cut.

## Stop and ask when

- The repeating lesion group cannot be identified in the EDC build.
- The item-group sequence cannot reach `SUPPTU`.
- A `Query Status` value appears that TEA-CTR-004 does not list. The sample
  contained only `Open` and `Closed`; `Answered` is assumed from the Veeva data
  model and has never been seen. Do not map a new value on your own judgement.
