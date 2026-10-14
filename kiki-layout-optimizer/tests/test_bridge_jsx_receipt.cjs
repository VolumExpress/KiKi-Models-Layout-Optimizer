/* File-based completion acknowledgements: fake Illustrator filesystem. */
const assert = require('assert');
const vm = require('vm');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname,'../illustrator');
const store = new Map();
let reads=0;
const project='/fake/repo';
function MockFolder(p){this.fsName=p;this.exists=true;this.parent={fsName:p.substring(0,p.lastIndexOf('/'))};}
function MockFile(p){this.fsName=p;this.parent=new MockFolder(p.substring(0,p.lastIndexOf('/')));}
Object.defineProperty(MockFile.prototype,'exists',{get(){return store.has(this.fsName);}});
MockFile.prototype.open=function(mode){this.mode=mode;return true;};
MockFile.prototype.read=function(){reads++;return store.get(this.fsName);};
MockFile.prototype.write=function(v){store.set(this.fsName,v);};
MockFile.prototype.close=function(){};
const ctx={File:MockFile,Folder:MockFolder,$:{fileName:project+'/illustrator/export_selection.jsx'},
  RegExp,Error,String,JSON};
ctx.kikiParseJSON=JSON.parse;
ctx.kikiStringify=JSON.stringify;
const source=fs.readFileSync(path.join(root,'bridge_receipt.jsxinc'),'utf8');
vm.runInNewContext(source,ctx);
ctx.kikiBridgeReceipt('export','ok','',project+'/workspace/Some/input_copy.json');
assert.strictEqual(store.size,0,'No GUI request should not write a receipt');
const nonce='ac'.repeat(16);
store.set(project+'/workspace/_bridge/request.json',JSON.stringify({nonce,action:'export'}));
ctx.kikiBridgeReceipt('export','ok','',project+'/workspace/Some/input_copy.json');
const data=JSON.parse(store.get(project+'/workspace/_bridge/'+nonce+'.json'));
assert.strictEqual(data.action,'export');
assert.strictEqual(data.status,'ok');
assert.strictEqual(data.nonce,nonce);
assert.ok(data.path.endsWith('input_copy.json'));
console.log('PASS ExtendScript receipt protocol with nonce and project workspace');
