---
name: study-configuration
description: Use when configuring a study for the Tumor Evaluation Review Agent — deriving the protocol configuration parameters from a protocol summary and an imaging charter, preparing or reviewing a protocol summary, extracting charter parameters, or resolving a conflict between what the protocol and the charter say. Covers APPLY slots A-03, A-07 and A-08. Trigger on mentions of protocol config, imaging charter, target lesion cap, confirmation window, measurability threshold, AC-11, or "configure the study".
---

# Study configuration for TEA

You are producing APPLY slots **A-03** (the protocol configuration, 28
parameters), **A-08** (the imaging charter extract), and supporting **A-07**
(the protocol summary). The contracts are `Charter_Requirements` (TEA-CTR-005,
34 charter parameters) and `Guideline_Profiles` in the programming
specification.

This is the most consequential APPLY work in the system. Every threshold the
rules read comes from here. A wrong parameter does not make the agent fail — it
makes the agent confidently wrong on every affected timepoint, and the agent
will look broken when it is the configuration that is broken.

## Two documents, and they disagree

The **protocol** is authoritative for what the study does: schedule, arms,
endpoints, treatment beyond progression. The **imaging charter** is
authoritative for how lesions are measured and read: measurability, slice
thickness, axis, reader paradigm, non-evaluable rules.

They overlap. Of the 34 charter parameters, 8 are routinely stated in the
protocol too and 10 more sometimes are — so up to half can disagree.

**A conflict is a finding, not a choice.** This is law L6. Do not resolve it by
preferring the charter, or the protocol, or the stricter value, or the one that
makes more findings go away. Silently preferring either buries a real
protocol-deviation risk inside a configuration file.

## How a parameter resolves

1. Read the charter extract and the protocol summary **independently**. Do not
   read one to fill gaps in the other on a first pass.
2. Record for every parameter which document it came from and the section
   within it. A parameter with no citation is not configured.
3. **Both agree** → set it, and record the agreement. That agreement is itself
   evidence worth keeping.
4. **Both disagree** → leave it `UNRESOLVED`. Present both values, both
   citations, and the rules that depend on it. The study team decides; record
   the decision and the person. The run does not start with an unresolved
   parameter that a live rule depends on.
5. **Only one supplies it** → use it, record the single source.
6. **Neither supplies it** → apply the guideline default and record it **as a
   default**, never as a source value. At audit, "RECIST 1.1 default, no
   study document stated it" and "the charter said 5" are different facts.

## The conflicts that actually occur

| Parameter | How they diverge |
|---|---|
| Confirmation interval | Protocol says 4 weeks; charter says 28 days from the scan. Usually the same, but not when the read lags. |
| Target lesion cap | Protocol restates RECIST 1.1 at 5; charter tightens to 3 for a tumour type. |
| Measurability threshold | Protocol says 10 mm; charter says twice slice thickness, and the study images at 7 mm — so 14 mm. |
| Brain imaging | Protocol requires baseline MRI for all; charter says when clinically indicated. |
| iRECIST scope | Protocol applies it to the immunotherapy arm; charter applies it to everyone. |

Every one of these changes findings. None can be settled without the study team.

## The parameters that matter most

Read all 34 on `Charter_Requirements`, but these are the ones where being wrong
is worst:

- **`criteria_version`** — RECIST 1.1, iRECIST, or both scoped to named arms.
  There is no safe default. Assuming RECIST 1.1 for an iRECIST study produces
  wrong progression calls on every treat-beyond-progression subject.
- **`criteria_modifications`** — if the charter alters a threshold, a cap or a
  progression definition, it has created a modified criteria set and the agent
  must be told explicitly. An unrecorded modification is the most dangerous
  silent assumption in the whole configuration.
- **`non_evaluable_rules`** — when a timepoint is not evaluable. Without it
  every gap becomes a finding, which is the largest source of avoidable query
  volume.
- **`slice_thickness_max_mm`** — measurability is a function of acquisition,
  which is why it lives in the charter rather than the protocol.
- **`confirmation_required` / interval** — the parameter most likely to differ
  between the two documents.
- **`new_lesion_standard`** and **`nt_progression_standard`** — these are quoted
  *verbatim* into the adjudication prompts, not paraphrased. The model is held
  to the standard the readers were actually given.

## The protocol summary (A-07)

The full protocol does not fit the prompt budget, so AC-11 reads a condensed
summary instead.

**It is prepared by hand, by the study data manager.** Not extracted by you, not
extracted by GLM. The selection rule — which sections go in — is a clinical
judgement agreed between the CDM and the Medical Monitor (open item OI-07).

Your role is to check it is sufficient, not to write it. If a parameter cannot
be resolved because the summary omits the relevant section, say which section is
missing and ask for it. Do not go to the full protocol and extract it yourself.

The summary carries a content hash that enters the run provenance, so a
configuration is always traceable to the exact document it came from.

## Done when

- Every parameter is either cited to a document and section, or explicitly
  recorded as a guideline default.
- Every conflict is listed with both values and a recorded study-team decision.
- AC-11 reports no unresolved parameter that a live rule depends on.
- The CDM has confirmed each checkpoint on screen S7.

## Stop and ask when

- The protocol summary is missing a section a parameter depends on.
- The charter and protocol conflict — always. Never pick.
- The charter appears to modify the published criteria. Confirm explicitly that
  it is a modification and that it is intended; this changes what the agent
  derives, and it needs the Medical Monitor.
- No imaging charter exists for the study. That is not a gap to work around —
  roughly half the parameters have no other source.
