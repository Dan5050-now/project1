# Changelog

All notable changes to the Tumor Evaluation Review Agent (TEA) artifacts.
Each artifact is versioned independently; see `docs/README.md` for the versioning policy.

## [Unreleased]

### Added — Step 1 and Step 2 draft deliverables (2026-08-10)

- **TEA-PLAN-001 Development Plan v0.1.0** (`docs/plan/development-plan.xml`)
  - Agent concept: deterministic-first / LLM-assisted split, 10-component pipeline,
    human-in-the-loop controls, explicit allowed/forbidden LLM task list, degraded
    (deterministic-only) mode.
  - LLM interoperability: provider interface with Anthropic, OpenAI-compatible (covers GLM
    gateways, vLLM, Ollama), GLM-native and null adapters; capability matrix and portability rules.
  - Canonical data model: 11 entities, relationships, ER diagram, SDTM (TU/TR/RS) and EDC
    mapping profiles.
  - Review scope: 7 rule families with risk weighting.
  - Architecture, deployment modes, data protection, web application concept and 7 planned screens.
  - Six-step delivery plan with entry/exit criteria per step.
  - 17 functional, 11 non-functional and 7 regulatory requirements; 14 risks with mitigations;
    validation approach; version control policy; quality metrics; 10 recommendations;
    14 open questions each with a stated working assumption.

- **TEA-SPEC-001 Programming Specification v0.1.0** (`docs/spec/programming-spec.xml`)
  - Guideline profiles for RECIST 1.0, RECIST 1.1 and iRECIST; 8 documented interpretation
    decisions for ambiguous areas.
  - 10 derivation algorithms in pseudocode (sum of diameters, nadir, percent changes, target /
    non-target / new-lesion / overall response, best overall response with confirmation,
    iRECIST state machine, progression dating).
  - **Rule catalog v0.1.0: 84 review points** — ST 5, BL 17, FU 14, RS 20, IR 10, XD 12, QM 6.
    Every rule carries intent, logic, severity, determination mode and the five reviewer-facing
    message templates.
  - LLM integration contract: provider interface, 5 prompt contracts, 6 guardrails
    (numeric injection, prompt-injection defence, no verdict authority, determinism, redaction,
    budget), conformance suite.
  - Query reconciliation algorithm, cascade grouping and prioritisation scoring.
  - Output specification, dedupe key, coverage report, API surface, error handling,
    performance, 8 test levels, configuration, extensibility procedures, traceability matrix.
  - 7 open specification questions for the Step 2 review.

- **TEA-CTR-001 canonical input contract** (`docs/contracts/canonical-input.schema.json`)
- **TEA-CTR-002 finding output contract** (`docs/contracts/finding.schema.json`)
- **Document control policy** (`docs/README.md`)

### Not started

Steps 3–6 (prototype output on dummy data, UI design, code generation, final application) are
gated on written approval of the two draft documents above.
