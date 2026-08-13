
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
