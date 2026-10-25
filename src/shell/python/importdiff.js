"use strict";
/* ============================================== the import difference report
   The screen for src/core/06a_diff.js, and the three questions around it.

   Wired into the PYTHON shell only. The web application is feature-frozen (N-06) and
   has no workspace to merge into - every load there starts fresh, by design - so the
   engine is shared and this screen is not. Loading a second file over a first in the
   web application still replaces, exactly as the reviewer signed it off.

   The order is specification sheet 09, and each step earns its place:

     1. nothing open, or an empty plan  ->  adopt it, ask nothing
     2. the plan holds data            ->  ASK FIRST. "Update it from <file>?"
     3. yes                            ->  the report, per sheet, accept or skip
     4. accepted                       ->  applied as PENDING EDITS

   Step 2 is the requester's addition at Q-N05, and it matters: going straight to a
   list of differences presumes an update was wanted at all, and somebody who opened
   the wrong file wants to be asked, not shown a table.

   The tick is per SHEET, not per row (S-N03). A row-level choice across a thousand
   rows is a choice nobody makes. Rows can still be LOOKED at - every sheet expands -
   because seeing what is about to change is a different act from choosing it.  */

(function () {
  const el = id => document.getElementById(id);

  /** The whole flow, from bytes to a plan. Returns true if anything was taken. */
  window.importSourceOver = async function (name, sheets) {
    const M = S.model;
    const hasData = !!M && ["Project", "Person", "Assignment"]
      .some(s => (M.raw[s] || []).some(r => !r.__new));

    if (!hasData) {                       // step 1 - nothing to merge into
      adopt(sheets, name);
      return true;
    }

    let incoming;
    try {
      incoming = buildModel(sheets);
    } catch (e) {
      showBanner("bad", `Could not read that file: ${e.message}`);
      return false;
    }
    if (incoming.fatal) {
      showBanner("bad", `${name} could not be read as a plan.`, incoming.findings);
      return false;
    }

    // Step 2. Ask before showing anything - see the note at the top.
    const go = await ask(
      "This plan already contains data",
      `<p>${esc(name)} is a source file. This plan already holds `
      + `${(M.raw.Project || []).filter(r => !r.__new).length} project(s) and `
      + `${(M.raw.Person || []).filter(r => !r.__new).length} person record(s).</p>`
      + `<p class="pm-note">Do you want to update this plan from that file? Nothing is `
      + `changed until you say which sheets to take, and nothing is saved until you `
      + `press Save.</p>`,
      "Show me what would change", "Leave this plan alone");
    if (!go) return false;

    const diff = importDiff(M.raw, incoming.raw);
    if (importDiffEmpty(diff)) {
      tell("Nothing to update",
        `<p>${esc(name)} holds nothing this plan does not already have. `
        + `No changes were made.</p>`);
      return false;
    }
    return report(name, diff);
  };

  /* ------------------------------------------------------------- the report */

  function report(name, diff) {
    return new Promise(resolve => {
      // Sheets with nothing to decide are listed but not offered - a tick box that
      // does nothing is a decision the reader has to make and then discover was empty.
      const live = REQUIRED_SHEETS.filter(s => diff[s].touched > 0);
      const accepted = new Set(live);

      const back = document.createElement("div");
      back.className = "pm-back";
      back.innerHTML = `<div class="pm-box" style="width:min(1080px,100%)">
        <h3>Update from ${esc(name)}</h3>
        <div class="pm-crumb" data-sum></div>
        <div class="body"><div data-sheets></div>
          <p class="pm-note" data-note></p></div>
        <div class="foot">
          <button class="btn" data-none>Take nothing</button>
          <span class="pm-grow"></span>
          <button class="btn" data-cancel>Cancel</button>
          <button class="btn primary" data-ok>Take the ticked sheets</button>
        </div></div>`;
      document.body.appendChild(back);
      const q = s => back.querySelector(s);

      const done = v => { back.remove(); document.removeEventListener("keydown", onKey);
                          resolve(v); };
      const onKey = e => { if (e.key === "Escape") done(false); };
      document.addEventListener("keydown", onKey);
      q("[data-cancel]").onclick = () => done(false);
      q("[data-none]").onclick = () => { accepted.clear(); paint(); };

      q("[data-ok]").onclick = () => {
        if (!accepted.size) { done(false); return; }
        const n = importApply(diff, accepted);
        rebuild(true);
        renderKeepingTab();
        back.remove();
        document.removeEventListener("keydown", onKey);
        const kept = [...accepted].filter(s => diff[s].touched);
        showBanner("", `Imported from ${name}: ${n.added} row(s) added and ${n.changed} `
          + `row(s) updated across ${kept.length} sheet(s). Nothing was removed. `
          + `These are UNSAVED CHANGES — press Save to keep them, or Leave without `
          + `change to put the plan back as it was.`);
        resolve(true);
      };

      const host = q("[data-sheets]");
      for (const s of REQUIRED_SHEETS) {
        const d = diff[s];
        if (!d.touched && !d.onlyHere.length) continue;
        host.appendChild(sheetBlock(d, accepted, paint));
      }

      function paint() {
        for (const cb of back.querySelectorAll("[data-sheet-tick]"))
          cb.checked = accepted.has(cb.dataset.sheetTick);
        const add = live.filter(s => accepted.has(s))
                        .reduce((n, s) => n + diff[s].add.length, 0);
        const chg = live.filter(s => accepted.has(s))
                        .reduce((n, s) => n + diff[s].change.length, 0);
        const keptRows = REQUIRED_SHEETS.reduce((n, s) => n + diff[s].onlyHere.length, 0);
        q("[data-sum]").innerHTML =
          `<button type="button" style="pointer-events:none">${add} row(s) to add</button>`
          + `<button type="button" style="pointer-events:none">${chg} row(s) to change</button>`
          + `<button type="button" style="pointer-events:none">${keptRows} row(s) only in `
          + `this plan — kept</button>`;
        q("[data-ok]").textContent = accepted.size
          ? `Take ${accepted.size} sheet(s)` : "Take nothing";
        q("[data-note]").textContent =
          "An accepted sheet ADDS and CHANGES rows. It never deletes: anything this plan "
          + "has and the file does not stays exactly where it is.";
      }
      paint();
    });
  }

  /** One sheet: a tick, a count, and the rows underneath on request. */
  function sheetBlock(d, accepted, paint) {
    const box = document.createElement("details");
    box.className = "pm-diff";
    const bits = [];
    if (d.add.length) bits.push(`${d.add.length} to add`);
    if (d.change.length) bits.push(`${d.change.length} to change`);
    if (d.onlyHere.length) bits.push(`${d.onlyHere.length} only here`);
    if (d.same) bits.push(`${d.same} unchanged`);

    box.innerHTML = `<summary>
        <label class="pm-tick"><input type="checkbox" data-sheet-tick="${d.sheet}"
          ${d.touched ? "" : "disabled"}></label>
        <b>${d.sheet}</b><span class="pm-sub">${bits.join(" · ") || "nothing"}</span>
      </summary><div class="pm-diff-body"></div>`;

    const tick = box.querySelector("input");
    tick.onclick = e => {
      e.stopPropagation();
      if (accepted.has(d.sheet)) accepted.delete(d.sheet); else accepted.add(d.sheet);
      paint();
    };
    box.querySelector("summary").onclick = e => {
      if (e.target.closest(".pm-tick")) e.preventDefault();
    };

    const body = box.querySelector(".pm-diff-body");
    body.appendChild(rowList("Would be added", d.add.map(r => ({
      label: diffLabel(d.sheet, r), detail: ""})), "add"));
    body.appendChild(rowList("Would be changed", d.change.map(ch => ({
      label: diffLabel(d.sheet, ch.row),
      detail: ch.cols.map(c => `${c.col}: ${diffShown(c.from)} → ${diffShown(c.to)}`)
                     .join("; ")})), "chg"));
    body.appendChild(rowList("Only in this plan — kept as they are",
      d.onlyHere.map(r => ({label: diffLabel(d.sheet, r), detail: ""})), "keep"));
    return box;
  }

  /** A capped list. Twelve rows is enough to see the shape of a change; the rest are
   *  counted, because a dialog that scrolls for a thousand rows is one nobody reads
   *  and everybody approves. */
  function rowList(title, items, kind) {
    const wrap = document.createElement("div");
    if (!items.length) return wrap;
    const CAP = 12;
    wrap.className = "pm-diff-list " + kind;
    wrap.innerHTML = `<h4>${title} <i>${items.length}</i></h4><ul></ul>`;
    const ul = wrap.querySelector("ul");
    for (const it of items.slice(0, CAP)) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="n"></span><span class="d"></span>`;
      li.querySelector(".n").textContent = it.label;
      li.querySelector(".d").textContent = it.detail;
      ul.appendChild(li);
    }
    if (items.length > CAP) {
      const li = document.createElement("li");
      li.className = "more";
      li.textContent = `…and ${items.length - CAP} more`;
      ul.appendChild(li);
    }
    return wrap;
  }

  /* ---------------------------------------------------------- small dialogs */

  function ask(title, html, yes, no) {
    return new Promise(resolve => {
      const back = document.createElement("div");
      back.className = "pm-back";
      back.innerHTML = `<div class="pm-box"><h3>${title}</h3>
        <div class="body">${html}</div>
        <div class="foot"><button class="btn" data-no>${no}</button>
          <button class="btn primary" data-yes>${yes}</button></div></div>`;
      document.body.appendChild(back);
      back.querySelector("[data-yes]").onclick = () => { back.remove(); resolve(true); };
      back.querySelector("[data-no]").onclick = () => { back.remove(); resolve(false); };
    });
  }

  function tell(title, html) {
    const back = document.createElement("div");
    back.className = "pm-back";
    back.innerHTML = `<div class="pm-box"><h3>${title}</h3><div class="body">${html}</div>
      <div class="foot"><button class="btn primary" data-ok>Close</button></div></div>`;
    document.body.appendChild(back);
    back.querySelector("[data-ok]").onclick = () => back.remove();
  }
})();
