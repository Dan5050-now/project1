# Tumor Evaluation Review Agent (TEA) — Document Control

This directory holds the controlled documents for the Tumor Evaluation Review Agent, an
AI-assisted data review agent for oncology clinical trials (RECIST / iRECIST).

## Repository layout

```
docs/
  README.md                      <- this file (document control policy)
  plan/development-plan.xml      <- TEA-PLAN-001  (Step 1 deliverable)
  spec/programming-spec.xml      <- TEA-SPEC-001  (Step 2 deliverable)
  contracts/
    canonical-input.schema.json  <- TEA-CTR-001  input data contract
    finding.schema.json          <- TEA-CTR-002  agent output (finding) contract
CHANGELOG.md                     <- human-readable change log across all artifacts
```

## Versioning policy

| Artifact | Versioning | Where the version lives |
|---|---|---|
| Development plan | SemVer (`MAJOR.MINOR.PATCH`) | `<documentControl><version>` |
| Programming specification | SemVer | `<documentControl><version>` |
| Rule pack (catalog of review points) | SemVer, independent of spec | `<ruleCatalog version=...>` |
| Prompt templates | SemVer per prompt | prompt registry (Step 5) |
| Agent output (findings) | Stamped, never versioned in place | `provenance` block in every finding |

Rules of thumb:

1. **Filenames carry no version.** The version lives inside the document and in the git
   tag. This keeps diffs reviewable (`git diff` on a stable path) instead of producing a
   new untracked file for every revision. Released versions are tagged
   `plan-vX.Y.Z`, `spec-vX.Y.Z`, `rulepack-vX.Y.Z`.
2. **MAJOR** = a change that invalidates previously issued findings or breaks a data
   contract. **MINOR** = new review points / new capability, backward compatible.
   **PATCH** = wording, typos, clarification with no logic change.
3. **Every agent run stamps its inputs**: engine version, rule pack version, prompt
   version, LLM provider + model id, guideline version, protocol config hash, and dataset
   snapshot hash. A finding can always be reproduced or explained after the fact.
4. **No silent rule edits.** Changing the logic of an existing rule requires a new rule
   pack MINOR/MAJOR and a `changeHistory` entry naming the rule id.

## Review status

| Document | Version | Status | Awaiting |
|---|---|---|---|
| TEA-PLAN-001 Development Plan | 0.1.0 | DRAFT | Sponsor review (Step 1 gate) |
| TEA-SPEC-001 Programming Specification | 0.1.0 | DRAFT | Sponsor review (Step 2 gate) |
| TEA-CTR-001/002 Data contracts | 0.1.0 | DRAFT | Follows spec approval |

Steps 3–6 (prototype output, UI design, code generation, final application) are **not
started** and are gated on written approval of the two draft documents above.

## Open questions

Open questions that block or shape the design are consolidated in
`plan/development-plan.xml` under `<openQuestions>`, each with an id (`OQ-nn`), the impact
of leaving it open, and the **working assumption** the drafts currently use. Answering
them is the main input to the Step 1 review meeting.
