# PRAP — analysing a resource plan with an AI

This guide covers three jobs for an AI working on a PRAP plan:

- **Diagnose:** score the plan 0–100, name what is short, overloaded or at risk, and
  read ahead.
- **Recommend:** propose assignment changes that fix a shortfall or relieve somebody
  who is overloaded.
- **What if:** answer a manager's question about a new project or a future situation.

It is written for two readers. The person sets the work up using sections 1–3. The AI
is given the prompt in section 4 and the files that section names.

> **One rule underlies everything below.** Code does the arithmetic and the AI
> explains it. A language model asked to total four thousand rows makes mistakes, and
> it gives a different score each time it is asked. So `tools/prap_analyze.py` computes
> every figure, and the AI interprets that output. Every what-if is recalculated by the
> real engine, never by the AI.

---

## 1. What you need

| File | Where it comes from | Used for |
|---|---|---|
| Calculated export, `*_CalculatedFTE_*.xlsx` | The application: **Export ▸ Calculated monthly FTE** (app 1.57 or later) | Diagnosis and recommendations |
| Source plan, `.xlsx` or `.prap.json` | **Export ▸ Source data**, or the workbook you load | What-if questions |
| `scorecard.json` / `.md` | `python tools/prap_analyze.py score <file>` | What the AI reads for a diagnosis |
| `comparison.json` / `.md` | `python tools/prap_analyze.py compare <before> <after>` | What the AI reads for a what-if |

**Export with no filter on,** unless you mean to analyse only part of the plan. The
export follows the screen. A filtered file says so on its ReadMe, and the scorecard
repeats the warning.

### 1.1 What the export carries for analysis (R-55)

| Sheet · column | Meaning |
|---|---|
| `ProjectMonth.demand_fte` | What the project's standard asks for that month. |
| `ProjectMonth.staffed_fte` | What its people are given, **the whole project**, whatever filter is on. |
| `ProjectMonth.gap_fte` | `staffed − demand`. Negative is short, positive is over. |
| `ProjectMonth.gap_dir` | `short` / `over` / `unallocated` / empty. `unallocated` means a month the periods ask for and nobody is on. |
| `PersonMonth.flag = unassigned` | The person is employed and on nothing that month (`fte` 0): **spare capacity**. |
| `Flags` with `project_id` | Project runs: short of standard, over standard, unallocated demand. |
| `Summary` | Standard demand, plus the totals of the three project kinds. |

> **Trap:** never add up `Detail.demand_fte`. It repeats the project's demand on every
> person's row, so the sum multiplies demand by headcount. Use
> `ProjectMonth.demand_fte`.

### 1.2 Where a shortage really shows

A PRAP project-month **is** its standard demand, divided among whoever is assigned
(REQ-CAL-19). So a project with too few people is **not** short on paper. Its people go
over the ceiling instead. A gap column only shows a shortage when somebody stated a
figure by hand (V-34) or when nobody is assigned at all (V-36).

The scorecard therefore gives every project a **hidden shortfall**: the overload of its
people above the ceiling, divided back among the projects that make it up. The total
across projects equals the total excess on people (`tools/test_analyze.py` checks
this). This number answers "which project is under-resourced"; the gap column alone
does not.

---

## 2. Data handling: do this before anything leaves your PC

The export contains **person names and departments**.

- Use only an AI service your company has approved for this kind of data, and follow
  your company's policy on what may be sent to it.
- Send the scorecard, not the raw export, wherever that is enough. It is smaller and
  it is already the answer to most questions.
- To remove names, add `--pseudonymise`. Names are dropped (people are referred to by
  `person_id`) and departments become codes (`D01`, `D02` …). The key is written to
  `pseudonym_key.csv` **beside the output. Keep that file; do not send it.**

```
python tools/prap_analyze.py score  MyPlan_CalculatedFTE_2026-10-04.xlsx --out analysis --pseudonymise
```

---

## 3. The three workflows

### 3.1 Diagnose

```
python tools/prap_analyze.py score <export.xlsx> --out analysis [--as-of YYYY-MM]
```

Give the AI `analysis/scorecard.json` and the prompt in section 4. `--as-of` sets where
the forward look starts. The default is the current month.

**The score.** There are five components. Each one is a ratio of "how much of X is in
trouble" and scores `weight × 0.5^(ratio ÷ half_at)`: full marks at 0, half at
`half_at`. The curve never reaches zero, so an improvement always shows, even on a
plan that is badly overloaded.

| Component | Weight | Ratio | Half at |
|---|---|---|---|
| `demand_coverage` | 35 | FTE-months short or unallocated ÷ standard demand | 0.05 |
| `over_allocation` | 25 | FTE-months above the ceiling ÷ FTE-months staffed | 0.10 |
| `concentration` | 15 | mean of the key-person ratio (one person carries over 60% of a project-month of ≥ 1.0 FTE) and the fragmentation ratio (person-months on 5 or more projects) | 0.15 |
| `plan_reliability` | 15 | Σ\|fte − automatic_fte\| ÷ the automatic total: how far hand-stated figures depart from the standard | 0.05 |
| `under_use` | 10 | person-months inside an under-allocation run ÷ person-months staffed | 0.10 |

| Band | Score |
|---|---|
| healthy | 85 or more |
| watch | 70–84 |
| at risk | 50–69 |
| critical | below 50 |

The weights are a starting point. Agree them with the people who use the score, change
`SCORING` in `tools/prap_analyze.py`, and bump its `version`, so that two scorecards
made under different weights are never compared. The score compares a plan with itself
over time and with a scenario. It is not an absolute grade.

**"Predictions."** The plan already *is* a forecast: every month ahead is in the file.
The forward look (`forward`, `monthly`) shows what is coming: the demand peak, the
months a shortfall starts, and how many person-months go over the ceiling in the next
six months. The AI should read those, not build a statistical forecast on top of them.

### 3.2 Recommend

`candidate_moves` in the scorecard lists, for each problem in the next six months of
its occurrence:

- **For a project:** the FTE-months it is missing, and the people who have room in
  *all* of those months, ranked by fit. Fit 3 means already on the project, 2 means has
  worked on the same type and phase, 1 the same type, 0 none.
- **For an overloaded person:** the project making up most of their peak, and the
  people with room to take some of it.

Room is `min(capacity_fte, ceiling) − current fte`. Months a person is not employed
count as no room.

**Candidates are where to look, not results.** Adding a person to a project changes
every share on it, so the real figures only come from re-running the engine. Before
recommending a move, test it as a what-if (3.3) and quote the comparison.

### 3.3 What if

1. Get the plan as text: `python tools/prap_io.py to-json plan.xlsx -o before.prap.json`
2. Copy it to `after.prap.json` and make the change as **rows**:
   - **New project:** `Project`, its `Milestone` dates, and `Assignment` rows. See
     `docs/PRAP_AI_Agent_Guide.md` §9.1.
   - **Somebody leaves:** set `Person.employment_end`, then end or reassign their
     `Assignment` rows.
   - **More or less effort:** `Assignment.person_weight`, or a `PersonPeriodWeight`
     window.
3. Check it: `python tools/prap_io.py validate after.prap.json`. Fix any error before
   going on.
4. Compare: `python tools/prap_analyze.py compare before.prap.json after.prap.json --out scenario`
5. Report from `scenario/comparison.json`: the score change, which components moved,
   which projects and people changed, and the next six months.

**Worked example** (the 10-project example plan, 2026-10 to 2028-09, as of 2026-10).
The scorecard ranked **PRJ-003** first, with 40.71 FTE-months of hidden shortfall. The
only person with room was **PSN-010**, who had 0.34 FTE spare. The scenario adds
PSN-010 to PRJ-003 as Clinical Data Associator from 2026-10, at `person_weight` 0.30:

```
PRJ-003: missing 40.71 → 34.02 FTE-months (hidden 40.71 → 34.02)
PSN-005: 21 → 8 months over the ceiling        PSN-010: 0 → 1
Next 6 months: hidden in overload 48.24 → 45.03; person-months over 43 → 41
Score 56.3 → 56.2: over_allocation +0.4, concentration +0.1, under_use −0.6
```

A good answer reports exactly this trade-off. The move relieves PSN-005 substantially.
It costs a little on under-use, because PSN-010 goes from free to lightly loaded, and
PSN-010 goes over the ceiling for one month. The plan as a whole is still overloaded:
one part-time person cannot fix a team that is short.

---

## 4. The prompt

Paste this as the instructions, then attach `scorecard.json` (or `comparison.json`):

```text
You are reviewing a clinical-project resource plan produced by PRAP. The attached
JSON was computed by a program from the plan; every figure in it is exact.

Rules:
1. Do not recompute, re-total or estimate any figure. Quote figures from the JSON,
   with the project_id / person_id and months they belong to.
2. If the question cannot be answered from the JSON, say so and say what would
   answer it (usually: a what-if run with prap_analyze.py compare).
3. A project's shortage has three parts: short, unallocated, and hidden (overload
   of its people above the ceiling, attributed back to it). Name the part.
4. Candidate moves are possibilities, not results. Do not state the effect of a move
   unless a comparison.json for it is attached.
5. Thresholds are absolute FTE (source.thresholds), not a share of capacity.
6. Mark anything you assume as an assumption.

Answer in this structure:
## Verdict        - score, band, and one sentence on why
## What drives it - the components that lose the most points, each with its inputs
## Top problems   - at most five: project or person, kind, size, months, and the
                    evidence (the JSON field)
## Coming up      - the next six months from forward/monthly: peaks, new shortfalls
## What to do     - at most five actions, each tied to a problem above and to
                    candidate_moves; say which need a what-if run before deciding
## Assumptions and limits
```

**Example questions**

- *Diagnose:* "Score this plan and tell me the three things most worth fixing this
  quarter."
- *Recommend:* "PRJ-003 is the biggest problem. Who could help in the next six months,
  and what should we test?"
- *What if:* attach `comparison.json` and ask "We are adding PSN-010 to PRJ-003 at
  0.3 from October. Is it worth it?"
- *New project:* "A Phase 3 study starts in March 2027. Draft the assignments, run the
  comparison, and tell me who it would overload." This needs an AI that can run the
  commands in 3.3. Otherwise, a person runs them and attaches the result.

---

## 5. Limits

- **The scorecard covers only the file it is given.** A filtered export gives a
  filtered scorecard, although the gaps in it are still whole projects.
- **"Room" is planned load against capacity.** It knows nothing about skills beyond
  role and project history, nor about leave, or work that is outside PRAP.
- **Hidden shortfall uses the over-allocation ceiling, not each person's capacity.**
  This matches how the application flags people. A part-timer at 1.2 FTE is
  overloaded in practice but is not counted.
- **Requires app 1.57 or later.** An older export has no demand or gap columns, and
  `prap_analyze.py` refuses it with that reason rather than scoring it as if nothing
  were short.

`tools/test_analyze.py` holds the scorecard to the application. A plan gives the same
scorecard whether it is read from the application's export or calculated from the
source plan by the Python reference.
