const APP_VERSION = "1.25";
const SCHEMA_EXPECTED = 6;

/* The controlled documents this build was written against (REQ-VC-01: plan,
   specification and outputs are version-controlled together and cross-referenced).
   Kept as data in one place, shown on screen, and checked against the repository by
   tools/check_consistency.py - a provenance label nobody verifies is one that quietly
   goes stale, which is the whole failure mode it exists to prevent. */
const BUILT_AGAINST = [
  {what:"Development plan",       file:"PRAP_Development_Plan_v2.27.xlsx",          ver:"2.27",
   status:"Baseline v2.0 APPROVED by Dan, 2026-08-02; v2.27 records Step 4 progress and schema 6"},
  {what:"Programming specification", file:"PRAP_Programming_Specification_v1.1.xlsx", ver:"1.1",
   status:"v1.0 APPROVED by Dan, 2026-08-02; v1.1 adds schema 6 — this document governs the code"},
  {what:"UI component list",      file:"PRAP_UI_Component_List_v1.0.xlsx",          ver:"1.0",
   status:"APPROVED by Dan, 2026-08-02 — Step 3 gate closed"},
  {what:"Source data template",   file:"PRAP_SourceData_Template_v1.8.xlsx",        ver:"1.8",
   status:`Schema version ${SCHEMA_EXPECTED} — the layout this application reads`},
  {what:"AI agent reference",     file:"PRAP_AI_Agent_Guide_v1.0.xlsx",             ver:"1.0",
   status:"Instructions for another program or AI agent; docs/prap_contract.json is its machine-readable half"},
];

