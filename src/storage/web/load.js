/** Read a dropped or chosen file into the application.
 *
 *  Two phases, each announced before it starts rather than after it ends, because both
 *  of them hold the main thread: parsing a large workbook is most of a second, and
 *  adopting it - validate, calculate, draw - is most of another. Between them the page
 *  cannot answer a click, so the least it can do is say what it is busy with.
 */
async function loadFile(file){
  document.body.classList.add("busy");
  try {
    showBanner("busy", `Reading ${file.name}…`);
    await paint();
    const isJson = /\.json$/i.test(file.name);
    const sheets = isJson ? readPrapJson(await file.text())
                          : await readWorkbook(await file.arrayBuffer());
    // The parse is done; what follows is the expensive half. Say so before it starts.
    showBanner("busy", `Building the plan from ${file.name}…`);
    await paint();
    adopt(sheets, file.name);            // replaces the banner with its own verdict
  } catch (e){
    showBanner("bad", `Could not read that file: ${e.message}`);
    console.error(e);
  } finally {
    document.body.classList.remove("busy");
  }
}
