---
name: validation-evidence
description: Use when deploying a Tumor Evaluation Review Agent installation or producing its computerised system validation evidence — deployment configuration, GLM gateway and network isolation, IQ, OQ, PQ records, traceability matrices, GAMP 5 categorisation, 21 CFR Part 11 or ICH E6(R3) mapping, or audit trail and ALCOA+ questions. Covers APPLY slots A-11 and A-12. Trigger on mentions of deployment, installation, validation, qualification, IQ/OQ/PQ, CSV, Part 11, GAMP, audit trail, or a regulatory inspection.
---

# Deploying and validating a TEA installation

You are producing APPLY slots **A-11** (the deployment configuration) and
**A-12** (the executed validation evidence for this installation). They are one
task: you configure the installation, then you qualify what you configured. The
*approach* is COMMON — sheet `Validation` in the development plan — and you
implement it. You do not design a local approach.

## Deployment configuration (A-11)

Containerised, on-premise. Gateway endpoint for GLM v5.2, database,
authentication, retention, backup.

**No external egress from any component.** This is not a hardening preference —
it is the reason REG-07 no longer gates release and the reason RSK-04 dropped to
negligible. Verify it rather than assuming it: an installation that can reach
the internet has a different risk profile from the one that was assessed.

The configuration is evidence in its own right. IQ below is where you record it.

## The distinction that matters

**Approach is COMMON. Evidence is APPLY.**

The risk categorisation, the test levels, the traceability structure and the
Part 11 mapping were settled once and apply everywhere. What you produce is the
executed record for *this* installation, *this* configuration, *this* data.

If the common approach does not fit the company's SOPs, that is a change request
(see `common-change-request`), not a locally invented alternative. Two
installations validated to two different approaches cannot be compared, and the
second one has to justify itself from scratch.

## Open item before you start

**OI-04 is not closed.** QA has not yet confirmed the validation deliverable
list. The assumption on record (OQ-14) is workable but unconfirmed, and
underestimating validation scope is logged as RSK-10.

Get QA's confirmation of the deliverable list *before* producing the package,
not during. Producing evidence against an unconfirmed list is how validation
work gets done twice.

## What the system's design already gives you

Much of the evidence exists as a by-product of the architecture. Use it rather
than re-creating it:

- **Determinism.** Every verdict is computed by code; the model narrates and
  adjudicates declared judgement points only. The same input produces the same
  findings. This is what makes conventional test evidence meaningful for an
  AI-assisted system, and it is the argument to lead with.
- **Verdict-identity testing.** GLM v5.2 output is compared against a
  deterministic-only reference on every commit. This is the mechanism proving a
  model cannot change a verdict — it replaced cross-provider conformance when
  the second provider was removed. It is the single most important piece of
  evidence in the package.
- **Run provenance.** Every run records rule pack version, prompt versions,
  model version, protocol and charter content hashes, conversion version and
  query file SHA-256. That is the reproducibility argument, already captured.
- **CI guards.** `check_catalog_drift.py`, `check_workbook_integrity.py` and
  `check_query_style.py`, each negative-tested. They run in the company too.
  A drift check that has never failed is not evidence; the negative test is.
- **Audit trail.** Every disposition and every version of a finding is recorded
  against a named person and time (AC-10).
- **Frozen, versioned rule pack.** 85 rules at 2.0.0, with change control. The
  catalog is the specification and the tested artifact at once.

## The parts that are genuinely yours

- **IQ** — the installed environment: versions, containers, database, GLM
  gateway endpoint, network isolation. Evidence that there is no external
  egress from any component.
- **OQ** — the system behaves as specified in *this* environment. The common
  test suite executed here, with results.
- **PQ** — it works for the intended use with real study data. The golden
  dataset (A-09) reviewed and accepted by CDM and the Medical Monitor.
- **Traceability matrix instance** — requirement → specification → test →
  result, for this installation.
- **Configuration qualification** — that the study configuration (A-03) traces
  to the protocol and charter documents by hash, and that every parameter is
  cited or recorded as a default.
- **Conversion qualification** — the SDTM conversion code (A-02) against its
  specification (A-01). This is often overlooked and it is upstream of
  everything.

## The question an inspector will ask

*"An AI wrote part of this system and an AI is in the review loop. How do you
know the output is right?"*

The answer has three parts, in this order:

1. **The model does not decide anything.** Code computes every verdict. The
   model narrates from structured evidence, adjudicates rules explicitly
   declared as judgement points, and reads free text. The boundary is declared
   per rule in the catalog, not left to runtime behaviour.
2. **That boundary is tested, not asserted.** Verdict identity against a
   deterministic-only reference, on every commit.
3. **A human adjudicates every finding.** The agent produces findings with a
   confidence rate; it does not change data and does not issue queries. The
   disposition is recorded against a person.

Have the evidence for each of the three ready to point at, not to describe.

## Done when

- The deployment configuration (A-11) is recorded, and no external egress is
  reachable from any component — verified, not assumed.
- A deterministic-only run completes end to end on the installation.
- QA has confirmed the deliverable list (OI-04) — before, not after.
- IQ, OQ and PQ records exist and are executed, not drafted.
- The traceability matrix instance is complete.
- The conversion qualification exists and names versions on both sides.
- QA accepts the package.

## Stop and ask when

- The common validation approach conflicts with a company SOP. Raise it; do not
  reconcile it locally.
- Any test in the common suite cannot be executed in this environment. A skipped
  test is reported as skipped, with the reason. Never recorded as passed.
