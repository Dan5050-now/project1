---
name: common-change-request
description: Use when work on the Tumor Evaluation Review Agent cannot be completed without changing a COMMON artifact — a rule, a derivation, a data contract, a prompt, the confidence model, the application, or the validation approach. Also use when a rule appears to be systematically wrong, when a study does not fit the rule pack, or when tempted to add a local override, patch or workaround. Trigger on mentions of changing a rule, rule pack, a false-positive rule, overriding behaviour, or "the agent is wrong about".
---

# When COMMON has to change

You have hit something you cannot do without editing a read-only artifact. That
is a legitimate and expected outcome. What follows is how to handle it — and
what not to do instead.

## Do not do these

- Edit a rule, a derivation, a contract or a prompt locally.
- Add a study-specific override, filter, exclusion list or post-processing step
  that changes which findings appear.
- Subclass, wrap or monkey-patch a COMMON component to change its behaviour.
- Fork a COMMON file "temporarily".
- Suppress a rule's output because it is noisy on this study.

Every one of these makes this installation a different agent from every other
one, while continuing to look like the same agent. The validation evidence then
covers something that is not what is running. Six months later nobody can tell
the local edit from a defect.

The prohibition is not about ownership. It is that a system claiming one
validated behaviour cannot have N of them.

## What to do instead

**1. Establish it is really a COMMON problem.**

Apply the test: would this artifact be identical for a different study, on a
different EDC, at a different company, using RECIST 1.1?

Most apparent rule problems are configuration problems. Before raising anything,
rule out:

- A parameter left at a guideline default because neither the protocol nor the
  charter supplied it.
- A protocol/charter conflict that was resolved by preference instead of being
  reported.
- An unrecorded modification to the published criteria in the charter — the
  agent implements published RECIST unless told otherwise, so every comparison
  is against the wrong standard.
- A conversion defect: merged reader streams, recomputed derived values,
  per-visit lesion ids, missing `TUMSTATE`, absent `RSCAT`.
- Missing query history, so nothing is suppressed as already-asked.

In practice most "this rule is wrong" reports are one of these. Check them
first; it is faster than a change request and it is usually the answer.

**2. Write it up.**

A usable change request contains:

- **The artifact and its version** — e.g. `TE-RS-014`, rule pack 2.0.0.
- **Observed behaviour**, with a concrete case: subject, visit, values, the
  finding produced.
- **Expected behaviour**, and the authority for it — the guideline clause, the
  charter section, or the clinical reasoning.
- **Why it is not configuration.** State which of the causes above you ruled out
  and how.
- **Scope**: does this affect one study or every study? A study-specific need is
  usually a new configuration parameter, not a rule change — say so if that is
  what you think.
- **Impact if unchanged**: how many findings, what severity, and whether the
  effect is false positives (noise) or false negatives (missed issues). These
  are not the same urgency.
- **Impact if changed**: findings already issued that would change. This is the
  part most often skipped and the part change control most needs.

**3. Send it back, and record the gap.**

The change request goes to the repository that owns COMMON. Meanwhile, record
the affected findings as a known limitation on the run, visible to reviewers.

Reviewers seeing a documented limitation can work around it. Reviewers seeing
silently filtered output cannot.

**4. Do not wait idle.**

Everything not blocked by the change continues. Only the affected findings are
held.

## Special cases

**A rule is noisy on this study but right in general.** That is configuration or
prioritisation, not a rule defect. Check whether a parameter should be set, or
whether the finding should be grouped as a consequence of a root cause rather
than raised per visit. Its confidence base rate may also be doing its job
already — a low-confidence finding is meant to sort downward, not to disappear.

**The company has its own query house style.** TEA-QS-001 is COMMON and
CI-enforced. A different house style is a legitimate change request. A local
edit to the templates silently disables the check that makes the style mean
anything.

**GLM v5.2 does not behave as the specification assumes.** The prompt budget and
structured-output behaviour were assumed against a generic gateway and never
verified against v5.2 — see TEA-GLM-001. This is expected to surface. It changes
the integration layer for everyone, so raise it centrally rather than working
around it locally.

**A guideline interpretation looks wrong.** The documented interpretations
ID-01 to ID-06 are deliberate choices where RECIST is ambiguous. Disagreeing
with one is a substantive clinical point and needs the Medical Monitor, not a
code change. Raise it as an interpretation change request and expect it to take
longer than a defect.

## Done when

- The change request is written, with a concrete case and an impact assessment
  on both sides.
- The limitation is recorded on the affected runs and visible to reviewers.
- No local edit to a COMMON artifact exists. Verify: `python3 tools/check_catalog_drift.py`
  must pass, and `git status` must show no modification under the read-only
  paths listed in `CLAUDE.md`.
