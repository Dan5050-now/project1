# TEP — Data Model and Derivation Specification

This annex defines where each element of the Tumor Evaluation Profile comes from and how every derived value is computed. It assumes CDISC SDTM as the collected layer and ADaM as the analysis layer, with RECIST 1.1 as the response criterion.

---

## 1. Source mapping by band

The mapping below is the contract between the report and the data. Where an ADaM dataset exists it is authoritative; SDTM is listed because a near-live review layer will often have to be built directly on it before ADaM is available.

### Band 1 — Patient characteristics

| Report element | SDTM | ADaM | Key variables |
|---|---|---|---|
| Demographics | `DM` | `ADSL` | `AGE`, `SEX`, `RACE`, `ETHNIC`, `COUNTRY`, `SITEID`, `ARM`/`ACTARM` |
| Baseline ECOG, height/weight/BSA | `VS`, `QS`/`RS` | `ADSL` | `VSTESTCD`, ECOG via `QSTESTCD`/`RSTESTCD` |
| Visit progress & on-study status | `SV`, `DS` | `ADSL` | `SVSTDTC`, `DSDECOD`, `DSTERM`, `EOSSTT`, `EOTSTT` |
| Primary cancer history & staging | `MH` (or study-specific `DD`/oncology-specific domain) | `ADSL` | `MHCAT='PRIMARY DIAGNOSIS'`, `MHSTDTC`, staging in `SUPPMH` or a custom domain |
| Biomarker / mutation status | `LB`, `FA`, or a genomics domain | `ADSL`/`ADLB` | study-specific |
| Metastatic sites at baseline | `MH` / `TU` (baseline records) | derived | `TULOC`, `MHTERM` |
| Prior anti-cancer therapy | `CM` (`CMCAT='PRIOR ANTINEOPLASTIC'`) | `ADCM` | `CMTRT`, `CMSTDTC`, `CMENDTC`, `CMINDC`, best response via `SUPPCM` |
| Prior surgical history | `PR` | `ADPR` | `PRTRT`, `PRSTDTC`, `PRCAT` |
| Prior radiotherapy | `PR` (`PRCAT='RADIOTHERAPY'`) | `ADPR` | `PRTRT`, `PRLOC`, `PRDOSE`, `PRSTDTC`/`PRENDTC` |
| Other medical history | `MH` | `ADMH` | `MHDECOD`, `MHBODSYS`, `MHSTDTC` |

### Band 2 — Disposition and exposure

| Report element | SDTM | ADaM | Key variables |
|---|---|---|---|
| Treatment exposure & cycles | `EX` | `ADEX` | `EXTRT`, `EXDOSE`, `EXDOSU`, `EXSTDTC`, `EXENDTC`, `VISIT`, `EPOCH` |
| Dose modifications | `EX` + `SUPPEX`, `AE` action taken | `ADEX` | `EXADJ`, `EXDOSFRQ`, `AEACN` |
| Visit schedule & actual visits | `TV`, `SV` | — | `VISITNUM`, `VISITDY`, `SVSTDTC` |
| Discontinuation | `DS` | `ADSL` | `DSDECOD`, `DSSTDTC`, `EOTSTT`, `DCSREAS` |
| DLT window and DLT events | study-specific `FA`/`AE` flag | `ADAE` | `AEDLT` flag (study-specific), DLT period from protocol |
| Survival follow-up | `DS`, `SS` | `ADSL`/`ADTTE` | `SSSTRESC`, `DTHDTC`, `DTHFL` |

### Band 3 — Tumor identification and evaluation

This is the CDISC oncology tumor package. The three domains are not independent — they are chained, and the chain is what makes drill-down possible.

| Report element | SDTM | ADaM | Key variables |
|---|---|---|---|
| Lesion identification (baseline & new) | `TU` | — | `TUSPID`, `TULNKID`, `TUTESTCD`, `TUORRES` (TARGET / NON-TARGET / NEW), `TULOC`, `TULAT`, `TUMETHOD`, `TUDTC`, `TUEVAL` |
| Lesion measurements over time | `TR` | `ADTR` | `TRLNKID`, `TRLNKGRP`, `TRTESTCD` (`LDIAM`, `LPERP`, `SAXIS`), `TRSTRESN`, `TRORRES`, `TREVAL`, `TRDTC`, `VISITNUM` |
| Timepoint & overall response | `RS` | `ADRS` | `RSLNKGRP`, `RSTESTCD` (`TRGRESP`, `NTRGRESP`, `OVRLRESP`, `BESTRESP`), `RSORRES`, `RSSTRESC`, `RSEVAL`, `RSDTC` |
| Derived SOD & % change | derived from `TR` | `ADTR` | `AVAL` (SOD), `BASE`, `CHG`, `PCHG`, `AVALC`, `PARAMCD='SUMDIAM'` |
| Nadir & change from nadir | derived | `ADTR` | nadir as a derived parameter, e.g. `PARAMCD='NADIR'`, `PCHGNAD` (study-defined) |
| Best overall response | derived from `RS` | `ADRS` | `PARAMCD='BOR'`/`'CBOR'`, `AVALC` |

**The linkage model.** `TU` assigns each lesion a `TULNKID`. `TR` records carry the same `TRLNKID`, which is how a measurement is attributed to a lesion, and carry `TRLNKGRP` grouping all measurements belonging to one assessment timepoint. `RS` carries the matching `RSLNKGRP`, which is how a response is attributed to the set of measurements that produced it. The TEP's drill-down requirement (FR-3-11) is therefore implemented by walking `RS.RSLNKGRP → TR.TRLNKGRP → TR.TRLNKID → TU.TULNKID`, and any study where these links are not populated will not support the drill-down without remediation. **Verify link population early — this is the most common blocker.**

### Band 4 — Relevant events

| Report element | SDTM | ADaM | Key variables |
|---|---|---|---|
| Adverse events | `AE` | `ADAE` | `AETERM`, `AEDECOD`, `AEBODSYS`, `AETOXGR`, `AESER`, `AEREL`, `AEACN`, `AEOUT`, `AESTDTC`, `AEENDTC`, `ASTDY`/`AENDY` |
| AESI / DLT flags | `AE` + `SUPPAE` | `ADAE` | `AESI` flag, study-specific DLT flag |
| Concomitant anti-cancer medication | `CM` | `ADCM` | `CMCAT`, `CMTRT`, `CMSTDTC`, `CMENDTC` |
| Palliative radiotherapy on study | `PR` | `ADPR` | `PRTRT`, `PRSTDTC`, `PRLOC` |

---

## 2. Derivation specification (RECIST 1.1)

The rules below are the report's computation contract. Where validated ADaM exists, the report must display ADaM values and use these rules only to *check* them; where the report computes them itself (pre-ADaM review layer), the output must be badged as unvalidated.

### 2.1 Target lesion selection and baseline

Target lesions are those identified at baseline as measurable and selected for follow-up, capped at **5 in total and 2 per organ** under RECIST 1.1. Measurability requires a longest diameter of at least 10 mm by CT/MRI (with slice thickness no greater than 5 mm), at least 20 mm by chest X-ray, or at least 10 mm by calliper for clinically assessed superficial lesions. Lymph nodes are the exception: a node is measurable and eligible as a target lesion only when its **short axis** is at least 15 mm, and it is the short axis — not the longest diameter — that enters the sum. Nodes with a short axis between 10 and 15 mm are recorded as non-target; nodes below 10 mm are considered non-pathological and are not recorded at all.

**Baseline SOD** is the sum, across all selected target lesions, of the longest diameter for non-nodal lesions and the short axis for nodal lesions, taken from the assessment closest to and prior to first dose. The report must state which visit was used as baseline, because protocols differ on whether screening or a later pre-dose scan is baseline.

```
SOD(t)      = Σ over target lesions L of  diameter(L, t)
                where diameter(L,t) = short axis for nodal L, longest diameter otherwise
SOD_base    = SOD(baseline visit)
SOD_nadir(t)= min( SOD(baseline), SOD(t') for all evaluable t' ≤ t )
```

### 2.2 Change metrics

```
CHG(t)      = SOD(t) − SOD_base                      (mm)
PCHG(t)     = 100 × ( SOD(t) − SOD_base ) / SOD_base            (%)
PCHGNAD(t)  = 100 × ( SOD(t) − SOD_nadir(t) ) / SOD_nadir(t)    (%)
ABSNAD(t)   = SOD(t) − SOD_nadir(t)                  (mm, needed for the ≥5 mm rule)
```

Both `PCHG` and `PCHGNAD` are required by the UI (FR-3-05) because response is defined against baseline while progression is defined against nadir. Reporting only one of them is the most common source of misread profiles.

### 2.3 Target lesion timepoint response

| Response | Rule |
|---|---|
| **CR** | Disappearance of all target lesions. Any pathological lymph node selected as target must have reduced to a **short axis below 10 mm**. |
| **PR** | `PCHG(t) ≤ −30%` — at least a 30% decrease in SOD relative to baseline, and CR not met. |
| **PD** | `PCHGNAD(t) ≥ +20%` **and** `ABSNAD(t) ≥ 5 mm` — both conditions must hold. Progression is also assigned on unequivocal progression of non-target disease or on the appearance of a new lesion, independent of SOD. |
| **SD** | Neither sufficient shrinkage for PR nor sufficient growth for PD, relative to the smallest sum on study. |
| **NE** | One or more target lesions not evaluated or not evaluable at the timepoint, such that a category cannot be assigned. |

The `≥ 5 mm` absolute requirement matters disproportionately in early-phase studies with low baseline burden, where a 20% relative increase can be clinically trivial. The report must expose the absolute value alongside the percentage for exactly this reason (FR-3-06).

### 2.4 Non-target and new lesions

Non-target lesions are assessed qualitatively, not measured: **CR** requires disappearance of all non-target lesions and normalisation of any tumor marker level; **Non-CR/Non-PD** covers persistence of one or more non-target lesions; **PD** requires *unequivocal* progression of existing non-target disease — a threshold deliberately set high, since modest non-target growth in the presence of target-lesion response should not drive an overall PD.

New lesions force an overall response of PD regardless of the target-lesion sum. Where a new lesion is equivocal — typically because it is too small to characterise — the assessment continues and the lesion is resolved at the next timepoint; if confirmed, progression is dated to the timepoint at which the equivocal lesion was **first observed**. The report must therefore carry both the first-observed date and the confirmation status for every new lesion (FR-3-10), because these two dates differ and the earlier one is the one that counts.

### 2.5 Overall timepoint response

Overall response at a timepoint is the standard RECIST 1.1 combination of the target response, the non-target response, and new-lesion status. The report should implement it as an explicit lookup table rather than as nested conditionals, so that it is inspectable and testable:

| Target | Non-target | New lesions | Overall |
|---|---|---|---|
| CR | CR | No | **CR** |
| CR | Non-CR/Non-PD | No | **PR** |
| CR | NE | No | **PR** |
| PR | Non-PD or NE | No | **PR** |
| SD | Non-PD or NE | No | **SD** |
| NE | Non-PD | No | **NE** |
| PD | Any | Yes or No | **PD** |
| Any | PD | Yes or No | **PD** |
| Any | Any | Yes | **PD** |

### 2.6 Confirmation and Best Overall Response

In studies where objective response rate is a primary or key secondary endpoint, a CR or PR must be **confirmed by a repeat assessment no less than 4 weeks after the criteria are first met**. SD, where it is being claimed, must additionally meet a protocol-defined minimum duration from first dose.

Best Overall Response is the best timepoint response recorded from first dose until progression or the start of new anti-cancer therapy, applying the confirmation requirement where the protocol requires it. The report must display BOR and state explicitly whether it is the confirmed or unconfirmed variant (FR-H-02) — showing an unconfirmed PR as "PR" without qualification is a material misrepresentation in an early-phase readout, and reviewers will catch it.

### 2.7 iRECIST extension (conditional)

Where the protocol specifies iRECIST — which applies when the asset is an immunotherapy and pseudoprogression is plausible — the response state machine gains two states. **iUPD** (immune unconfirmed progressive disease) is assigned when RECIST 1.1 progression criteria are met: a rise of at least 20% and at least 5 mm from nadir, unequivocal non-target progression, or a new lesion. If the patient is clinically stable, treatment may continue and a confirmatory scan is performed **no earlier than 4 weeks and no later than 8 weeks** after the iUPD. **iCPD** (confirmed progressive disease) is assigned when that scan shows further progression. If instead the burden falls back, the iUPD is treated as pseudoprogression, the level of suspicion **resets**, and a subsequent progression event is again assigned as iUPD, restarting the confirmation cycle.

The reset behaviour is what makes iRECIST awkward to render, and it is why FR-3-13 asks for iUPD to be a distinct visual state on the burden curve rather than a variant marker: a patient may legitimately accumulate several iUPD episodes, and a reviewer must be able to count them.

---

## 3. Data quality checks the profile should surface

The profile is a natural place to expose the inconsistencies that listings hide, and doing so costs very little once the data is assembled. Each check below should render as an inline, non-blocking flag on the relevant band.

| Check | Trigger | Where flagged |
|---|---|---|
| Target lesion count exceeds RECIST limits | more than 5 target lesions, or more than 2 in one organ | Baseline inventory (band 3c) |
| Nodal lesion selected on longest diameter | nodal target lesion where `TRTESTCD` is not the short axis | Baseline inventory |
| Missing measurement at a performed visit | `TR` record absent for a target lesion at a visit with an `RS` record | Per-lesion row (band 3b) |
| Response without supporting measurements | `RS` record whose `RSLNKGRP` matches no `TR` records | Burden curve marker |
| Method change between visits | `TRMETHOD` differs from baseline for the same lesion | Per-lesion row |
| Assessment outside protocol window | actual assessment date deviates from the scheduled window | Disposition band (band 2) |
| Overdue assessment | no assessment within the window and subject still on treatment | Header status + band 2 |
| PD without corroboration | overall PD derived where neither new lesion, non-target PD, nor the ≥20%/≥5 mm target rule is satisfied | Burden curve marker |
| Nadir precedes baseline | derived nadir date earlier than the baseline assessment date | Burden curve |
| Response after new anti-cancer therapy | timepoint response dated after start of subsequent therapy in `CM` | Burden curve + band 4 |
