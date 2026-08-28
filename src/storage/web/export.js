
function exportWorkbook(asJson){
  if (S.pending.length){
    showBanner("bad", `Export held — ${S.pending.length} change${S.pending.length===1?" is":"s are"} `
      + `not yet saved. Press Save to keep them, or Leave without change to discard them, then export.`);
    return;
  }
  // A row inserted but never filled has no identifier, so nothing could ever reference
  // it and re-importing would silently drop it. Refuse, and name it.
  const incomplete = [];
  for (const s of REQUIRED_SHEETS){
    const key = KEY_COL[s];
    if (!key) continue;
    for (const r of S.model.raw[s]){
      if (!r.__new) continue;
      if (!r[key]){ incomplete.push(`${s} (${key} is empty)`); continue; }
      // A row carrying nothing but what the application put there is an empty record,
      // and the identifier alone would not make it one on re-import either.
      if (isSkeleton(s, r))
        incomplete.push(`${s} (a new row has nothing in it but the values the `
          + `application supplied)`);
    }
  }
  if (incomplete.length){
    showBanner("bad", `Export blocked — ${incomplete.length} new row(s) would be lost `
      + `on re-import: ${[...new Set(incomplete)].join("; ")}. Fill them in or delete them.`);
    return;
  }
  const sheets = {};
  for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
  const blob = asJson ? new Blob([buildPrapJson(sheets)], {type:"application/json"})
                      : buildXlsx(sheets);
  const stamp = new Date().toISOString().slice(0,10);
  const base = (S.fileName || "PRAP_SourceData.xlsx").replace(/\.prap\.json$|\.json$|\.xlsx$/i, "");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  // Never silently overwrite the source: the stamp, and a different extension for the
  // two forms, keep the workbook and its text twin distinguishable on disk.
  a.download = `${base}_${stamp}${asJson ? ".prap.json" : ".xlsx"}`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  S.saved = 0; S.editedCells.clear();
  for (const s of REQUIRED_SHEETS) for (const r of S.model.raw[s]) delete r.__new;
  renderAll(); showTab(S.tab);
  showBanner("", `Exported ${a.download}. ${asJson
    ? "The same data as plain text — another program or an AI agent can read it directly, "
      + "and this application loads it straight back. "
    : ""}The source file on disk is untouched.`);
}


/* ------------------------------------------------------ the calculated figures
   The other export, and deliberately a different thing. See core/06b_results.js for
   what is in the file and why it is kept apart from the source workbook.

   Two things it does NOT do, both on purpose:
     * it does not refuse over unsaved changes the way the source export does. That
       refusal exists so a plan cannot be exported half-written and re-imported; this
       file is a snapshot for reading, and a snapshot of what is on screen right now
       is exactly what somebody pressing it wants. The ReadMe carries the count of
       unresolved findings so the reader knows what state it was taken in.
     * it does not clear the saved-changes marker. Nothing has been written back to
       the plan, so the plan is no less in need of exporting than it was before. */
function exportResults(){
  const M = S.model, C = S.calc;
  if (!M || !C){ showBanner("bad", "Nothing to export yet — load a workbook first."); return; }
  const months = grid();
  if (!months.length){
    showBanner("bad", "Export held — the horizon covers no months. Widen it, or press "
      + "'Expand to all projects', and try again.");
    return;
  }
  const named = Object.entries(S.f)
    .filter(([, set]) => set.size)
    .map(([k, set]) => `${FILTER_LABEL[k] || k}: ${[...set].join(", ")}`);
  const stamp = new Date().toISOString().slice(0, 16).replace("T", " ");
  const sheets = buildResults(M, C, {
    months, projects: activeProjects(), people: activePeople(),
    filters: named.join(" · "), fileName: S.fileName, stamp,
  });

  const day = new Date().toISOString().slice(0, 10);
  const base = (S.fileName || "PRAP").replace(/\.prap\.json$|\.json$|\.xlsx$/i, "");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(buildXlsx(sheets));
  a.download = `${base}_CalculatedFTE_${day}.xlsx`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);

  const rows = sheets.Detail.length - 1;
  showBanner("", `Exported ${a.download} — ${rows.toLocaleString()} assignment-month `
    + `row(s) across ${sheets.ProjectMonth.length - 1} project-month(s) and `
    + `${sheets.PersonMonth.length - 1} person-month(s)`
    + (named.length ? `, for what is currently in view (${named.join("; ")})` : "")
    + `. This one is for reading — it cannot be imported back. Your plan and the source `
    + `file on disk are both untouched.`);
}

/** How each filter is named to a reader who was not looking at the screen. */
const FILTER_LABEL = {type:"Project type", phase:"Clinical phase", out:"Work scope",
                      proj:"Project", pers:"Person", role:"Role", dept:"Department"};
