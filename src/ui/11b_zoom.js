/* ============================================== 11b. one section, the whole screen */

/* WHY. The page is 1400px wide at most and every scroll region is deliberately bounded
 * on both axes (REQ-DSH-13), which is right for reading and wrong for typing: the
 * entry tables cap at 340px, so a twenty-two column sheet is filled in through a window
 * about a fifth of its own size, and every committed cell costs a re-scroll in two
 * directions. The complaint was about entering data, not about looking at it, so this is
 * for the panels that hold the tables - the charts get it too because the rule that
 * decides which panels offer it is "is there a bounded region in here", which is the
 * honest test rather than a list somebody maintains.
 *
 * HOW, AND WHY NOT THE OBVIOUS WAY. The panel is not moved anywhere. Every edit commits
 * through renderKeepingTab(), which replaces a whole pane's innerHTML - so a node lifted
 * out into an overlay would be orphaned by the first keystroke that was saved, which is
 * precisely the keystroke the full screen exists for. A <dialog> opened with showModal()
 * has that fault and a worse one: it makes the rest of the document inert, and the rest
 * of the document is where the Save button is.
 *
 * So the panel stays exactly where it is in the DOM and is DRESSED as full screen -
 * position:fixed, the viewport for a box. Nothing is detached, so every delegated
 * handler in the application keeps working without knowing this feature exists: the cell
 * editor, the type-ahead, the column filters, the tooltips, the legend picks. What has to
 * survive a re-render is one small object in S, and applyZoom() puts the class back on
 * whichever panel now carries that name.
 *
 * WHICH IS WHY PANELS HAVE NAMES. data-panel on each of them, and the state holds the
 * name rather than an element or an index. An element does not survive the render. An
 * index does not survive the data: selecting a different project changes how many panels
 * its detail section draws, and the heading cannot be the key either, because half of
 * them end in the name of the row that is selected - "Periods - IMM-106 Phase 2" is a
 * different string for every project and the same section throughout.
 *
 * THE STICKY BAND IS LIFTED ABOVE IT, NEVER COVERED. A full screen that hides the Save
 * button is a trap: the reader fills in a wide comfortable table and then has nowhere to
 * commit it, and the one thing this feature is for is editing. So #stickybar - the edit
 * state, Save, Leave without change, and the tabs - is promoted to the top of the
 * viewport and the panel starts underneath it. The filter bar above it IS covered, and
 * that is the trade: Escape brings the whole page back, and the per-column filters, which
 * are the ones used while entering data, are inside the tables and come with them.
 */

/** Panel names are ours, from the templates in 11_tabs / 12b_manual / 13c_gap, so the
 *  selector is built rather than escaped - but only after checking the name looks like
 *  one of ours, because a name that reached a selector unchecked would be the one place
 *  in this file where state could become markup. */
const ZOOM_NAME = /^[a-z][a-z0-9-]*$/;

/** The element the state currently names, or null if nothing is drawn under that name. */
function zoomTarget(){
  const z = S.zoom;
  if (!z || !ZOOM_NAME.test(z.name) || z.tab !== S.tab) return null;
  const sec = el(z.tab);
  return sec ? sec.querySelector(`.panel[data-panel="${z.name}"]`) : null;
}

/* The pop-up is the same on every one of these buttons, so it says what the thing IS -
   including what it does not cover, because the filter bar going behind it is the one
   surprise, and a reader who meets that without warning reads it as a fault. */
const ZOOM_HELP =
  "<b>Full screen</b><br>Give this section the whole window. The table or chart keeps "
  + "every column it has and grows to the height of the screen, which is what makes a wide "
  + "sheet usable to type into.<br><br>Editing works exactly as it does here, and the bar "
  + "at the top stays with you — the tabs, the unsaved-change count and <b>Save</b>. The "
  + "filter bar goes behind it; each table's own column filters come with it. "
  + "<b>Esc</b> brings the page back.";

/** Put the full-screen state back after a render, and keep every button in step with it.
 *
 *  Called at the end of renderTab() and from showTab(), which between them cover every
 *  path that can redraw or reveal a pane - so there is no code anywhere else that has to
 *  remember this feature exists. It is idempotent, and with no zoom open it does nothing
 *  but the one pass that labels the buttons.
 */
function applyZoom(){
  const t = zoomTarget();
  // The section it named is not on screen any more - a tab change, a different project
  // selected, a view toggled from a matrix to rows. Drop it rather than leave a state
  // nothing can be seen to be in.
  if (S.zoom && !t) S.zoom = null;
  for (const p of document.querySelectorAll(".panel.zoom"))
    if (p !== t) p.classList.remove("zoom");
  if (t) t.classList.add("zoom");
  document.body.classList.toggle("zoomed", !!t);
  zoomButtons();
  fitZoom();
}

/** The button, added here rather than written into the panel templates.
 *
 *  A render replaces each panel wholesale, so the markup would have to carry the button in
 *  all thirty-one places a panel is emitted and keep every one of them in step; one pass
 *  after each render cannot drift. It is also the only way the label can say CLOSE on the panel that is open
 *  without every template knowing about the state.
 *
 *  A panel with no bounded region is offered nothing. There is nothing to enlarge in a
 *  panel of prose or a panel whose message is that there is no data, and a control that
 *  does nothing visible teaches the reader that the feature is broken.
 */
function zoomButtons(){
  for (const p of document.querySelectorAll("section.tab .panel[data-panel]")){
    const head = p.querySelector(":scope > .phead");
    if (!head) continue;
    let b = head.querySelector(":scope > button.zoombtn");
    if (!p.querySelector(".scrollx")){ if (b) b.remove(); continue; }
    if (!b){
      b = document.createElement("button");
      b.type = "button";
      b.className = "btn tiny zoombtn";
      b.setAttribute("data-tip", ZOOM_HELP);
      head.appendChild(b);
    }
    const on = p.classList.contains("zoom");
    b.dataset.zoom = p.dataset.panel;
    b.setAttribute("aria-pressed", on ? "true" : "false");
    /* The WORD carries the state, not a colour and not a glyph (D-04). "Full screen"
       went out with an up-down arrow at first and the arrow was the wrong statement -
       it reads as "make this taller", which is half of what happens - and a symbol
       outside the common range is a tofu box on whatever font the next PC has. The
       cross on Close is kept because it is in every font there is and means exactly
       one thing. */
    b.innerHTML = on ? "&#10005; Close" : "Full screen";
    b.title = on ? "Back to the page (Esc)" : "Give this section the whole window";
  }
}

/** How much room is taken above the section, measured rather than assumed.
 *
 *  Two things can be up there and neither is a constant.
 *
 *  THE EDIT BAR wraps on a narrow window and its guide text changes length as you work,
 *  so its height moves WHILE the screen is open - the band grows the moment the first
 *  unsaved change appears. Read after the class is on, so the figure is the one the band
 *  has while fixed rather than the one it had in the flow.
 *
 *  AND THE SHELL MAY HAVE ITS OWN BAR ABOVE THAT. The web page has nothing there; the
 *  Python and desktop shells both put a title strip and a status strip at the top of the
 *  window, above everything this layer draws. ui/ must not know their markup, so the
 *  shells declare themselves with data-topchrome and this measures whatever answers -
 *  which is also why the figure is taken from the DOM rather than from a stylesheet
 *  constant per shell, three of which would have to be kept in step by hand.
 *
 *  An element that has scrolled away is not above the section any more, so anything whose
 *  top has left the upper half of the window is not counted.
 */
function fitZoom(){
  const on = document.body.classList.contains("zoomed");
  let chrome = 0;
  if (on) for (const e of document.querySelectorAll("[data-topchrome]")){
    const r = e.getBoundingClientRect();
    if (r.height > 0 && r.top < innerHeight / 2) chrome = Math.max(chrome, Math.round(r.bottom));
  }
  const bar = el("stickybar");
  const h = (on && bar) ? Math.round(bar.getBoundingClientRect().height) : 0;
  const root = document.documentElement.style;
  root.setProperty("--zoomchrome", chrome + "px");
  root.setProperty("--zoomtop", (chrome + h) + "px");
}

/** Open the named section full screen, or close whatever is open.
 *
 *  The caller re-measures the scroll regions afterwards - the shell owns those bars, and
 *  every region in the panel has just changed size by a factor of three.
 */
function setZoom(tab, name){
  S.zoom = name ? {tab, name} : null;
  applyZoom();
  // Focus is the caller's: the control is inside the panel's own head, so putting it
  // back on the control - which the shell does, because the control is relabelled rather
  // than replaced - already leaves the keyboard inside the section. Doing it here as well
  // would be two things moving the focus and only one of them winning.
}
