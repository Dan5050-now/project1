const APP_VERSION = "1.30";
const SCHEMA_EXPECTED = 8;

/* The controlled documents this build was written against (REQ-VC-01: plan,
   specification and outputs are version-controlled together and cross-referenced).
   Kept as data in one place, shown on screen, and checked against the repository by
   tools/check_consistency.py - a provenance label nobody verifies is one that quietly
   goes stale, which is the whole failure mode it exists to prevent. */
const BUILT_AGAINST = [
  {what:"Development plan",       file:"PRAP_Development_Plan_v2.32.xlsx",          ver:"2.32",
   status:"Baseline v2.0 APPROVED by Dan, 2026-08-02; v2.32 records Step 4 progress, schema 8, the absorption rule and the retirement of V-28"},
  {what:"Programming specification", file:"PRAP_Programming_Specification_v1.6.xlsx", ver:"1.6",
   status:"v1.0 APPROVED by Dan, 2026-08-02; v1.5 adds schema 8 and the absorption rule, v1.6 retires V-28 — this document governs the code"},
  {what:"UI component list",      file:"PRAP_UI_Component_List_v1.0.xlsx",          ver:"1.0",
   status:"APPROVED by Dan, 2026-08-02 — Step 3 gate closed"},
  {what:"Source data template",   file:"PRAP_SourceData_Template_v1.10.xlsx",       ver:"1.10",
   status:`Schema version ${SCHEMA_EXPECTED} — the layout this application reads`},
  {what:"AI agent reference",     file:"PRAP_AI_Agent_Guide_v1.0.xlsx",             ver:"1.0",
   status:"Instructions for another program or AI agent; docs/prap_contract.json is its machine-readable half"},
];

