/* ============================================================ 1. ZIP + XLSX read
   An .xlsx is a ZIP of XML parts. Read the central directory from the end of the
   file, then inflate each entry we need. Written out rather than vendored so the
   application stays one offline file (decision D-01).                          */

const td = new TextDecoder();

async function inflateRaw(bytes){
  const ds = new DecompressionStream("deflate-raw");
  const stream = new Blob([bytes]).stream().pipeThrough(ds);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function unzip(buf){
  const dv = new DataView(buf), u8 = new Uint8Array(buf);
  // End of central directory: signature 0x06054b50, scanned backwards because the
  // record carries a variable-length comment.
  let eocd = -1;
  for (let i = u8.length - 22; i >= 0 && i > u8.length - 65558; i--){
    if (dv.getUint32(i, true) === 0x06054b50){ eocd = i; break; }
  }
  if (eocd < 0) throw new Error("Not a .xlsx file — no ZIP directory found.");
  const count = dv.getUint16(eocd + 10, true);
  let off = dv.getUint32(eocd + 16, true);
  const files = {};
  for (let n = 0; n < count; n++){
    if (dv.getUint32(off, true) !== 0x02014b50) break;
    const method = dv.getUint16(off + 10, true);
    const csize  = dv.getUint32(off + 20, true);
    const nlen   = dv.getUint16(off + 28, true);
    const elen   = dv.getUint16(off + 30, true);
    const clen   = dv.getUint16(off + 32, true);
    const lho    = dv.getUint32(off + 42, true);
    const name   = td.decode(u8.subarray(off + 46, off + 46 + nlen));
    // The local header repeats the name and extra field, at its own lengths.
    const lnlen = dv.getUint16(lho + 26, true), lelen = dv.getUint16(lho + 28, true);
    const start = lho + 30 + lnlen + lelen;
    files[name] = { method, data: u8.subarray(start, start + csize) };
    off += 46 + nlen + elen + clen;
  }
  const out = {};
  for (const [name, f] of Object.entries(files)){
    if (!/\.(xml|rels)$/i.test(name)) continue;
    out[name] = td.decode(f.method === 0 ? f.data : await inflateRaw(f.data));
  }
  return out;
}

const XP = new DOMParser();
function xml(s){ return XP.parseFromString(s, "application/xml"); }

function colNum(ref){                       // "BC12" -> 0-based column index
  let n = 0;
  for (const ch of ref){
    const c = ch.charCodeAt(0);
    if (c < 65 || c > 90) break;
    n = n * 26 + (c - 64);
  }
  return n - 1;
}

/** Read every sheet into { sheetName: [ [cell,...], ... ] }, values as string|number. */
async function readWorkbook(buf){
  const parts = await unzip(buf);
  const shared = [];
  if (parts["xl/sharedStrings.xml"]){
    for (const si of xml(parts["xl/sharedStrings.xml"]).getElementsByTagName("si")){
      // <si> may hold one <t> or several inside <r> runs; concatenate in order.
      shared.push(Array.from(si.getElementsByTagName("t")).map(t => t.textContent).join(""));
    }
  }
  const rels = {};
  for (const r of xml(parts["xl/_rels/workbook.xml.rels"]).getElementsByTagName("Relationship")){
    rels[r.getAttribute("Id")] = r.getAttribute("Target").replace(/^\/?xl\//, "");
  }
  const sheets = {};
  for (const sh of xml(parts["xl/workbook.xml"]).getElementsByTagName("sheet")){
    const name = sh.getAttribute("name");
    const rid = sh.getAttribute("r:id") || sh.getAttributeNS(
      "http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id");
    const target = "xl/" + rels[rid];
    const doc = xml(parts[target] || "");
    const rows = [];
    for (const row of doc.getElementsByTagName("row")){
      const cells = [];
      for (const c of row.getElementsByTagName("c")){
        const i = colNum(c.getAttribute("r") || "");
        const t = c.getAttribute("t");
        let v;
        if (t === "inlineStr"){
          v = Array.from(c.getElementsByTagName("t")).map(x => x.textContent).join("");
        } else {
          const vEl = c.getElementsByTagName("v")[0];
          const raw = vEl ? vEl.textContent : null;
          // A formula cell with no cached result is written <v/>, and Number("") is 0.
          // Reading that as zero turns every uncalculated derived cell into a real value.
          if (raw === null || raw === "") { v = null; }
          else if (t === "s") v = shared[+raw];
          else if (t === "str" || t === "e") v = raw;
          else if (t === "b") v = raw === "1";
          else { const n = Number(raw); v = isFinite(n) ? n : raw; }
        }
        if (i >= 0) cells[i] = (v === "" ? null : v);
      }
      rows.push(cells);
    }
    sheets[name] = rows;
  }
  return sheets;
}

