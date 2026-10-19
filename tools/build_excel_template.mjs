import fs from 'node:fs/promises';
// Run with the Codex primary runtime from an OS temporary directory with
// @oai/artifact-tool available. Pass the repository root as the first argument.
const repo=process.argv[2];if(!repo)throw Error('Pass repository root');
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const w=Workbook.create(),p=w.worksheets.add('Preventivo'),c=w.worksheets.add('Calcolo interno');
const aqua='#2C829B',navy='#193B4B',pale='#EDF6F8';
function text(s,cell,value){s.getRange(cell).values=[[value]];}
function band(s,range,color){s.getRange(range).format.fill=color;s.getRange(range).format.font={bold:true,color:color===pale?navy:'#FFFFFF'};}
for(const s of [p,c]){s.showGridLines=false;s.tabColor=aqua;s.getRange('A1:L20').format.font={name:'Arial',size:11,color:navy};s.getRange('A1:L20').format.rowHeight=24;s.getRange('A1:L20').format.wrapText=true;s.getRange('A1:L20').format.verticalAlignment='center';}
[19,43,7,9,16,17].forEach((v,i)=>p.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}20`).format.columnWidth=v);
p.mergeCells('A2:C2');text(p,'A2','PREVENTIVO');p.getRange('A2').format.font={size:25,bold:true,color:navy};p.getRange('A2').format.rowHeight=38;
p.mergeCells('A4:C4');text(p,'A4','Data');band(p,'A5:F5',aqua);p.getRange('A5:F5').format.rowHeight=5;
['GHIRARDELLI MARCO — Ghiro Tech and Light','Via Giacomo Bresadola 5 · 38025 Dimaro Folgarida (TN)','P. IVA 02834310399 · REA TN-254793','mghirardelli@pec.perind.it'].forEach((v,i)=>{p.mergeCells(`A${i+6}:C${i+6}`);text(p,`A${i+6}`,v)});
for(let r=6;r<=9;r++)p.mergeCells(`D${r}:F${r}`);
text(p,'D6','CLIENTE');p.getRange('D6').format.font={bold:true,color:aqua};
p.mergeCells('A11:F12');text(p,'A11','Oggetto del preventivo');p.getRange('A11').format.font={size:16,bold:true,color:navy};
p.getRange('A13:F15').format.rowHeight=8;
p.getRange('A16:F16').values=[['Appartamento / zona','Descrizione','U.M.','Quantità','Prezzo unitario','Importo']];band(p,'A16:F16',aqua);p.getRange('A16:F16').format.rowHeight=34;
p.getRange('A17:F17').values=[['Zona','Descrizione','cad',1,0,0]];p.getRange('A17:F17').format.rowHeight=42;p.getRange('D17').setNumberFormat('0.00');p.getRange('E17:F19').setNumberFormat('"€" #,##0.00');
band(p,'A18:F18',pale);band(p,'A19:F19',navy);p.freezePanes.freezeRows(16);
p.images.add({dataUrl:'data:image/jpeg;base64,'+(await fs.readFile(repo+'/ghiro_preventivi/logo.jpg')).toString('base64'),anchor:{from:{row:0,col:3},extent:{widthPx:290,heightPx:105}}});
[22,20,58,9,12,18,16,20,20,20].forEach((v,i)=>c.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}20`).format.columnWidth=v);
c.mergeCells('A1:J1');text(c,'A1','GHIRO TECH — CALCOLO INTERNO');band(c,'A1:J1',navy);c.getRange('A1:J1').format.rowHeight=34;
c.mergeCells('A2:J2');text(c,'A2','Modifica i dati azzurri: i prezzi e il foglio Preventivo si aggiornano con le formule.');
['Sconto materiali','Ricarico','IVA'].forEach((v,i)=>text(c,`A${i+4}`,v));c.getRange('B4:B6').values=[[0],[0],[0.22]];c.getRange('B4:B6').setNumberFormat('0.00%');c.getRange('B4:B6').format.fill=pale;c.getRange('B4:B6').format.font={color:'#0070C0'};
c.getRange('A8:J8').values=[['Appartamento / zona','Codice','Descrizione','U.M.','Quantità','Costo unitario','Quota materiale','Costo scontato','Prezzo cliente','Importo cliente']];band(c,'A8:J8',aqua);c.getRange('A8:J8').format.rowHeight=38;
c.getRange('A9:J9').values=[['Zona','COD','Descrizione','cad',1,0,0,0,0,0]];c.getRange('A9:G9').format.fill=pale;c.getRange('A9:G9').format.font={color:'#0070C0'};c.getRange('A9:J9').format.rowHeight=42;c.getRange('E9').setNumberFormat('0.00');c.getRange('F9:J9').setNumberFormat('"€" #,##0.00');c.getRange('G9').setNumberFormat('0.00%');c.freezePanes.freezeRows(8);
w.recalculate();
console.log((await w.inspect({kind:'table',range:'Preventivo!A16:F19',include:'values,formulas',tableMaxRows:4,tableMaxCols:6})).ndjson);
const output=await SpreadsheetFile.exportXlsx(w);
await output.save('template.xlsx');
await fs.writeFile(repo+'/ghiro_preventivi/quote_template.b64',(await fs.readFile('template.xlsx')).toString('base64')+'\n');
