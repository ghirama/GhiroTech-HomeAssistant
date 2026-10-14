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
main.run("newConfig();addRoom();gcAddBox(0);gcBoxes(rooms[0])[0].note='Nota originale';gcPut(0,0,0);duplicateApartment();rooms[1].scatole[0].note='Nota copia';addApartment('Parti comuni');addRoom()");
assert.equal(main.run('apartments.length'),3);
assert.equal(main.run("rooms[0].scatole[0].note"),'Nota originale');
assert.equal(main.run("apartments[2].nome"),'Parti comuni');
main.run('toQuote();lines.forEach(r=>r.prezzo=10);render()');
assert.equal(main.run('new Set(lines.map(r=>r.appartamento)).size'),3);
const total=main.run('calc().subtotal');assert.ok(total>0);
assert.match(main.get('totals').innerHTML,/Parti comuni/);
main.run('lines=[];gcQuote()');assert.equal(main.run('new Set(lines.map(r=>r.appartamento)).size'),2);
assert.equal(main.run("lines.filter(r=>r.codice==='FR-presa').length"),2);
main.run("apartments=[];rooms=[{nome:'Legacy'}];normalizeApartments()");assert.equal(main.run('rooms[0].appartamento_id'), 'app-1');
const editor=await load('editor.html');
editor.run("room().items.push({id:'point',type:'comando',fruits:['Presa'],note:'Originale'});applyPDF({id:'pdf-a',url:'first.png',width:100,height:100,pagine:2,pagina:1});addApartment('Appartamento 2',true);room().items[0].note='Copia';applyPDF({id:'pdf-b',url:'second.png',width:100,height:100,pagine:2,pagina:2});addApartment('Parti comuni')");
assert.equal(editor.run('apartments.length'),3);
assert.equal(editor.run('rooms[0].items[0].note'),'Originale');
assert.notEqual(editor.run('rooms[0].items[0].id'),editor.run('rooms[1].items[0].id'));
assert.equal(editor.run('rooms[0].planDoc.id'),'pdf-a');assert.equal(editor.run('rooms[1].planDoc.id'),'pdf-b');
assert.equal(editor.run('rooms[2].planDoc'),undefined);
console.log('Apartment transitions, independent copies, common areas, quote grouping and per-apartment PDF: OK');
