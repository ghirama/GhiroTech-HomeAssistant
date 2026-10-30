// Manual editor operations and calculation parity, without browser dependencies.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync('ghiro_preventivi/index.html','utf8');
const script=html.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];
function fn(name){const start=script.indexOf('function '+name+'(');assert(start>=0,name);let n=0,begin=script.indexOf('{',start),end=begin;for(;end<script.length;end++){if(script[end]==='{')n++;if(script[end]==='}'&&!--n)break;}return script.slice(start,end+1)}
const context={structuredClone,lines:[{prezzo:100,quantita:2,quota_materiale:50,sconto:10,ricarico_voce:20}],render(){},$:id=>({value:{discount:20,markup:10,vat:22}[id]})};vm.createContext(context);
vm.runInContext(['manualCost','calc','duplicateQuoteLine','moveQuoteLine'].map(fn).join('\n'),context);
assert(Math.abs(context.calc().subtotal-213.84)<1e-8);
context.duplicateQuoteLine(0);context.lines[1].prezzo=25;assert.equal(context.lines[0].prezzo,100);
context.moveQuoteLine(0,1);assert.equal(context.lines[0].prezzo,25);context.moveQuoteLine(0,-1);assert.equal(context.lines[0].prezzo,25);
console.log('Manual editor: independent duplication, order, bounds and totals OK');
