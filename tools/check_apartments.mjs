// Run the real inline frontend scripts with a small DOM adapter to test state transitions.
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
function environment(){
 const nodes=new Map();
 const node=()=>({value:'',innerHTML:'',textContent:'',style:{},classList:{add(){},remove(){},toggle(){}},addEventListener(){},insertAdjacentElement(){},replaceChildren(){},append(){},add(){},focus(){},removeAttribute(){},showModal(){},close(){},querySelectorAll(){return [node(),node(),node()]}});
 const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)};
 const context=vm.createContext({console,structuredClone,crypto:globalThis.crypto,alert(){},confirm:()=>true,Option:function(text,value){return {text,value}},document:{getElementById:get,createElement:node,querySelectorAll:()=>[],querySelector:()=>null},fetch:async()=>({ok:true,json:async()=>[]}),setTimeout,URL,Blob});
 context.window=context;return {context,get};
}
async function load(name){const env=environment();const html=await readFile(new URL('../ghiro_preventivi/'+name,import.meta.url),'utf8');for(const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))vm.runInContext(match[1],env.context);return {...env,run:code=>vm.runInContext(code,env.context)};}
const main=await load('index.html');
main.run("newConfig();addRoom();gcAddBox(0);gcBoxes(rooms[0])[0].note='Nota originale';gcPut(0,0,0);duplicateApartment();rooms[0].scatole[0].note='Nota copia';addApartment('Parti comuni');addRoom();roomSet(0,'luci',1)");
assert.equal(main.run('apartments.length'),3);
assert.equal(main.run("rooms[2].scatole[0].note"),'Nota originale');
assert.equal(main.run("apartments[0].nome"),'Parti comuni');
main.run('toQuote();lines.forEach(r=>r.prezzo=10);render()');
assert.equal(main.run('new Set(lines.map(r=>r.appartamento)).size'),3);
const total=main.run('calc().subtotal');assert.ok(total>0);
assert.match(main.get('totals').innerHTML,/Parti comuni/);
main.run('lines=[];gcQuote()');assert.equal(main.run('new Set(lines.map(r=>r.appartamento)).size'),2);
assert.equal(main.run("lines.filter(r=>r.codice==='FR-presa').length"),2);
main.run("apartments=[];rooms=[{nome:'Legacy'}];normalizeApartments()");assert.equal(main.run('rooms[0].appartamento_id'), 'app-1');
// Counts follow fruit operations, not occupied module slots.
main.run("newConfig();addRoom();gcAddBox(0);gcSelected='schuko';gcPut(0,0,0)");
assert.equal(main.run('rooms[0].preseSchuko'),1);
main.run("gcCloneBox(0,0)");assert.equal(main.run('rooms[0].preseSchuko'),2);
main.run("gcDeleteFruit(0,0,0)");assert.equal(main.run('rooms[0].preseSchuko'),1);
main.run("gcRemoveBox(0,1)");assert.equal(main.run('rooms[0].preseSchuko'),0);
main.run("roomSet(0,'comandi',2);roomSet(0,'luci',3);gcSelected='deviatore';gcPut(0,0,0)");
assert.equal(main.run('rooms[0].comandi'),3);assert.equal(main.run('rooms[0].luci'),3);
main.run("roomSet(0,'comandi',0)");assert.equal(main.run('rooms[0].comandi'),1);
main.run("gcDeleteFruit(0,0,0)");assert.equal(main.run('rooms[0].comandi'),0);
// Legacy totals already including boxes are not counted twice; repeated render is stable.
main.run("rooms=[{nome:'Legacy',prese10:2,luci:2,scatole:[{moduli:3,frutti:['presa','presa']}]}];normalizeApartments();renderRooms();renderRooms()");
assert.equal(main.run('rooms[0].prese10'),2);
main.run("gcSelected='presa';gcPut(0,0,2)");assert.equal(main.run('rooms[0].prese10'),3);
main.run("rooms=JSON.parse(JSON.stringify(rooms));renderRooms()");assert.equal(main.run('rooms[0].prese10'),3);
const editor=await load('editor.html');
editor.run("room().items.push({id:'point',type:'comando',fruits:['Presa'],note:'Originale'});applyPDF({id:'pdf-a',url:'first.png',width:100,height:100,pagine:2,pagina:1});addApartment('Appartamento 2',true);room().items[0].note='Copia';applyPDF({id:'pdf-b',url:'second.png',width:100,height:100,pagine:2,pagina:2});addApartment('Parti comuni')");
assert.equal(editor.run('apartments.length'),3);
assert.equal(editor.run('rooms[2].items[0].note'),'Originale');
assert.notEqual(editor.run('rooms[2].items[0].id'),editor.run('rooms[1].items[0].id'));
assert.equal(editor.run('rooms[2].planDoc.id'),'pdf-a');assert.equal(editor.run('rooms[1].planDoc.id'),'pdf-b');
assert.equal(editor.run('rooms[0].planDoc'),undefined);
console.log('Apartment transitions, independent copies, common areas, quote grouping and per-apartment PDF: OK');

// Prepending keeps existing room/box order and targets the new box.
main.run("newConfig();addRoom();roomSet(0,'nome','Cucina');gcAddBox(0);gcUpdateBox(0,0,'nome','Originale');gcAddBox(0)");
assert.equal(main.run('rooms[0].scatole[0].nome'),'Scatola 2');
assert.equal(main.run('gcBox'),0);
main.run('gcCloneBox(0,1)');assert.equal(main.run('rooms[0].scatole[0].nome'),'Originale 2');
main.run('addRoom()');assert.equal(main.run('rooms[0].nome'),'Ingresso');assert.equal(main.run('rooms[1].nome'),'Cucina');
main.run('duplicateApartment()');assert.equal(main.run('apartments[0].id'),main.run('activeApartment'));assert.equal(main.run('rooms[0].nome'),'Ingresso');assert.equal(main.run('rooms[1].nome'),'Cucina');

// New devices count as one point each, with capacity based on occupied modules.
main.run("newConfig();addRoom();gcAddBox(0);gcSelected='presenza2';gcPut(0,0,0);gcPut(0,0,1)");
assert.equal(main.run('rooms[0].scatole[0].frutti.length'),1);
assert.equal(main.run('rooms[0].extra'),1);
main.run("gcSelected='ronzatore';gcPut(0,0,2);gcQuote()");
assert.equal(main.run('rooms[0].extra'),2);
assert.equal(main.run("lines.filter(r=>r.codice==='FR-presenza2').length"),1);
main.run("gcUpdateBox(0,0,'moduli',6);gcDeleteFruit(0,0,0);gcSelected='campanello';gcPut(0,0,3);gcSelected='presenza1';gcPut(0,0,0);rooms=JSON.parse(JSON.stringify(rooms));renderRooms()");
assert.equal(main.run('rooms[0].extra'),3);
main.run("delete rooms[0].punti_extra_scatole.extra;rooms[0].extra=5;renderRooms();gcDeleteFruit(0,0,0)");assert.equal(main.run('rooms[0].extra'),4);
editor.run("room().items=[{id:'sensor-test',fruits:[]}];selected='sensor-test';$('capacity').value='3';$('fruit').value='Sensore di presenza 2 moduli';fruitAdd();fruitAdd()");
assert.equal(editor.run('item().fruits.length'),1);
editor.run("$('fruit').value='Ronzatore';fruitAdd()");assert.equal(editor.run('usedFruitModules(item())'),3);
editor.run("item().fruits=[];$('fruit').value='Campanello';fruitAdd();fruitAdd()");assert.equal(editor.run('item().fruits.length'),1);assert.equal(editor.run('usedFruitModules(item())'),3);

for(const env of [main,editor]){
 assert.equal(env.run("nextCopyName('Scatola 1',['Scatola 1','Scatola 3'])"),'Scatola 4');
 assert.equal(env.run("nextCopyName('Camera',['Camera','Camera 2'])"),'Camera 3');
 assert.equal(env.run("nextCopyName('Scatola 1 (copia)',['Scatola 1','Scatola 2'])"),'Scatola 3');
}
main.run('newConfig();addRoom();gcAddBox(0);gcCloneBox(0,0);gcCloneBox(0,1)');assert.equal(main.run('rooms[0].scatole[0].nome'),'Scatola 3');
main.run('duplicateApartment();duplicateApartment()');assert.equal(main.run('apartments[0].nome'),'Appartamento 3');

// Absolute click positions, holes, contiguous capacity and independent save round trips.
main.run("newConfig();addRoom();gcAddBox(0);gcSelected='presa';gcPut(0,0,2)");
assert.equal(main.run('JSON.stringify(rooms[0].scatole[0].frutti)'),JSON.stringify([null,null,'presa']));
main.run("gcSelected='schuko';gcPut(0,0,1)");assert.equal(main.run('rooms[0].preseSchuko'),0);
main.run("gcPut(0,0,0);gcDeleteFruit(0,0,0)");assert.equal(main.run('JSON.stringify(rooms[0].scatole[0].frutti)'),JSON.stringify([null,null,'presa']));
main.run("rooms=JSON.parse(JSON.stringify(rooms));renderRooms();lines=[];gcQuote()");assert.equal(main.run("lines.filter(r=>r.codice==='FR-presa').length"),1);
main.run("gcUpdateBox(0,0,'moduli',4);gcSelected='termostato3';gcPut(0,0,0)");assert.equal(main.run('rooms[0].extra'),0);

main.run("newConfig();addRoom();gcAddBox(0);gcSelected='presa';gcPut(0,0,2);gcPresets=[{id:1,nome:'Modello',serie:'Vimar Plana',scatola_json:JSON.stringify(rooms[0].scatole[0])}];gcSetSeries(0,'BTicino Living Now');gcInsertPreset(0,1)");
assert.equal(main.run('rooms[0].scatole[0].serie'),'BTicino Living Now');assert.equal(main.run('rooms[0].scatole[1].serie'),'Vimar Plana');
main.run("jdAdd(0);jdSet(0,0,'quantita',2);jdClone(0,0);jdSet(0,0,'formato','custom');jdSet(0,0,'larghezza',222);jdSet(0,0,'note','Dati');rooms=JSON.parse(JSON.stringify(rooms));renderRooms();lines=[];gcQuote()");
assert.equal(main.run("lines.filter(r=>r.codice.startsWith('DER-')).reduce((n,r)=>n+r.quantita,0)"),4);
assert.ok(main.run("lines.some(r=>r.descrizione.includes('BTicino Living Now'))"));
assert.ok(main.get('gcDetails').innerHTML.includes('222 ×'));
main.run('duplicateApartment()');assert.equal(main.run('rooms[0].derivazioni[0].larghezza'),222);
main.run("jdSet(0,0,'larghezza',333)");assert.equal(main.run('rooms[1].derivazioni[0].larghezza'),222);
