async function loadFile(file){
  try {
    showBanner("", `Reading ${file.name}…`);
    const isJson = /\.json$/i.test(file.name);
    const sheets = isJson ? readPrapJson(await file.text())
                          : await readWorkbook(await file.arrayBuffer());
    adopt(sheets, file.name);
  } catch (e){
    showBanner("bad", `Could not read that file: ${e.message}`);
    console.error(e);
  }
}
