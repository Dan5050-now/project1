# project1 — Tumor Evaluation Profile (TEP)

Design work for a **Tumor Evaluation Profile**: an individual-patient, treatment-effect-focused review report for an ongoing early-phase (Ph1/1b) oncology trial.

Unlike a conventional patient profile — which is organised by CRF domain and optimised for completeness — the TEP is organised around a single shared time axis and carries only the data needed to interpret tumor burden and response. It exists so a medical monitor, clinical scientist, or investigator can judge, at the level of one patient, whether an observed change in tumor burden is real and drug-attributable.

## Documents

| Document | Contents |
|---|---|
| [`docs/tumor-evaluation-profile/01-concept-and-requirements.md`](docs/tumor-evaluation-profile/01-concept-and-requirements.md) | Framing, external precedents, users, concept options and recommendation, information architecture, functional and non-functional requirements, delivery phasing, open decisions |
| [`docs/tumor-evaluation-profile/02-data-model-and-derivations.md`](docs/tumor-evaluation-profile/02-data-model-and-derivations.md) | CDISC SDTM/ADaM source mapping per band, TU/TR/RS linkage model, full RECIST 1.1 derivation spec, iRECIST extension, data-quality checks |
| [`docs/tumor-evaluation-profile/03-visual-and-interaction-spec.md`](docs/tumor-evaluation-profile/03-visual-and-interaction-spec.md) | Layout geometry, time axis, encoding rules per band, interaction model, accessibility and export |
| [`docs/tumor-evaluation-profile/mockup/tumor-evaluation-profile.html`](docs/tumor-evaluation-profile/mockup/tumor-evaluation-profile.html) | Interactive mockup of the four-band profile with fabricated sample data — open in a browser, or view the published version: **[Tumor Evaluation Profile mockup](https://claude.ai/code/artifact/becb87d6-f74c-41b0-89e9-21934412b9de)** |

> The mockup is a design artefact. All subject data in it is fabricated and it must not be used with real patient data as-is.

## Summary of the recommendation

Build an **interactive single-subject review application** over ADaM (or a curated SDTM-derived review layer), with the static one-page PDF as an export path from the same page and a deliberately thin cohort layer as the entry point. Do not start from the PDF and retrofit interactivity — the per-lesion drill-down never fits afterwards.

The page is four bands: patient characteristics (no time axis), disposition and exposure, tumor evaluation, and relevant events. The last three share one synchronised study-day axis, which is what lets a reviewer read concurrency directly rather than assembling it mentally.

Three commitments differentiate this from a generic profile:

- **The derived response is never shown without its inputs** — every SOD, percent change, and response category drills down to the lesion measurements that produced it, via the CDISC `--LNKID`/`--LNKGRP` chain.
- **Per-lesion behaviour is first-class** — heterogeneous response, where some lesions shrink while others grow, is exactly the early-phase signal that aggregate SOD hides.
- **Data quality is visible, not smoothed over** — non-evaluable timepoints break the burden curve rather than being interpolated across.

## Scope basis

- **Data standard:** CDISC SDTM (`TU` / `TR` / `RS` plus `DM`, `DS`, `EX`, `AE`, `CM`, `PR`, `MH`) and ADaM (`ADSL`, `ADTR`, `ADRS`, `ADAE`)
- **Response criteria:** RECIST 1.1, with iRECIST specified as a conditional extension for immunotherapy assets

## Sources

Research grounding for the design, with the external precedents it draws on:

- [RECIST 1.1 — EORTC RECIST Committee](https://recist.eortc.org/recist-1-1/)
- [New response evaluation criteria in solid tumours: revised RECIST guideline (version 1.1) — full guideline PDF](https://project.eortc.org/recist/wp-content/uploads/sites/4/2015/03/RECISTGuidelines.pdf)
- [RECIST 1.1 — Update and Clarification: From the RECIST Committee (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5737828/)
- [Revised RECIST Guideline Version 1.1: What Oncologists Want to Know and What Radiologists Need to Know (AJR)](https://www.ajronline.org/doi/10.2214/AJR.09.4110)
- [iRECIST — EORTC RECIST Committee](https://recist.eortc.org/irecist/)
- [iRECIST: how to do it (Cancer Imaging)](https://link.springer.com/article/10.1186/s40644-019-0281-x)
- [Another Look at SDTM Oncology Tumor Packages (PharmaSUG 2017, DS07)](https://pharmasug.org/proceedings/2017/DS/PharmaSUG-2017-DS07.pdf)
- [Deconstructing ADRS: Tumor Response Analysis Data Set (PharmaSUG 2016, DS08)](https://pharmasug.org/proceedings/2016/DS/PharmaSUG-2016-DS08.pdf)
- [Efficacy ADaMs in Oncology — Step by Step (PhUSE US 2020, SI07)](https://www.lexjansen.com/phuse-us/2020/si/SI07.pdf)
- [Creating ADTR — admiralonco vignette (pharmaverse)](https://pharmaverse.github.io/admiralonco/main/articles/adtr.html)
- [Unleashing Potential of Graphs for Oncology Trials (PhUSE US 2018, DV08)](https://www.lexjansen.com/phuse-us/2018/dv/DV08.pdf)
- [Waterfall vis-a-vis Spider plots: Complex oncology efficacy visualisations (WUSS 2023, Paper 174)](https://www.wuss.org/proceedings/2023/WUSS-2023-Paper-174.pdf)
- [Visualization of Oncology data from Interactive Dashboards (PharmaSUG China 2021, DV068)](https://pharmasug.org/proceedings/china2021/DV/Pharmasug-China-2021-DV068.pdf)
- [Tumor Response Visualization in Clinical Trial Oncology (JMP Discovery Summit 2018)](https://community.jmp.com/kvoqx44227/attachments/kvoqx44227/Discovery-Summit-2018-Presentations/37/1/Miclaus_TumorResponse_US2018.pdf)
- [Disease Response Swimmer Plot — JMP Clinical documentation](https://www.jmp.com/support/downloads/JMPC71_documentation/Content/JMPCUserGuide/OP_C_ON_0001.htm)
- [Swimmer Plots for Clinical Trials in Clinical Oncology — The Miller Lab](https://themillerlab.io/posts/swimmer_plots/)
- [3D waterfall plots: a better graphical representation of tumor response in oncology (Annals of Oncology)](https://www.annalsofoncology.org/article/S0923-7534(19)31972-6/fulltext)
- [Analysis and Visualization of Longitudinal Genomic and Clinical Data in cBioPortal (Cancer Research, 2023)](https://aacrjournals.org/cancerres/article/83/23/3861/730145/Analysis-and-Visualization-of-Longitudinal-Genomic)
- [cBioPortal clinical-timeline (GitHub)](https://github.com/cBioPortal/clinical-timeline)
- [teal.modules.clinical — standard clinical outputs for CDISC data (Roche/Genentech, pharmaverse)](https://insightsengineering.github.io/teal.modules.clinical/main/)
- [CDISC-compliant clinical trial imaging management system focusing on tumor response assessment data (J Biomed Inform)](https://www.sciencedirect.com/science/article/pii/S1532046421001118)
