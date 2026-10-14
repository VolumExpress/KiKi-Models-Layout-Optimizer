/* Test Illustrator selection-to-constraint matching, no actual Illustrator. */
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const helper=fs.readFileSync('illustrator/json_helpers.jsxinc','utf8');
const jsx=fs.readFileSync('illustrator/cep_constraints.jsxinc','utf8');
const P='/project/workspace/Test';
let files={};
const objects=[
 {id:'0',uuid:'uuid-0',name:'item-0',source_bounds_pt:[0,10,10,0]},
 {id:'1',uuid:'uuid-1',name:'P10-SYM-007__5.5mm',source_bounds_pt:[20,10,30,0]}
];
files[P+'/input_copy.json']=JSON.stringify({schema:1,document_name:'Test.ai',objects});
files[P+'/result_test.json']='old';
files['/project/illustrator/json_helpers.jsxinc']=helper;
function File(path){this.fsName=String(path).replace(/\\/g,'/');this.encoding='UTF-8';}
Object.defineProperty(File.prototype,'exists',{get(){return Object.prototype.hasOwnProperty.call(files,this.fsName);}});
File.prototype.open=function(mode){this.mode=mode;this.buffer='';return true;};
File.prototype.read=function(){return files[this.fsName]};
File.prototype.write=function(text){this.buffer+=text;};
File.prototype.close=function(){if(this.mode==='w')files[this.fsName]=this.buffer;};
File.prototype.remove=function(){delete files[this.fsName];return true;};
File.prototype.rename=function(newName){let target=this.fsName.replace(/[^/]+$/,newName);files[target]=files[this.fsName];delete files[this.fsName];return true;};
function Folder(path){this.fsName=path;this.exists=true;}
const selection=[{uuid:'uuid-1',geometricBounds:[20,10,30,0]}];
const doc={name:'Test.ai',selection};
const context={app:{documents:[doc],activeDocument:doc},File,Folder,confirm:()=>true,
  $:{evalFile(){}},JSON,Error,String,Number,isFinite,RegExp,Math};
vm.createContext(context);vm.runInContext(helper+'\n'+jsx,context);
let r=JSON.parse(context.kikiCepSetSelectedRules('/project',true,'0'));
assert.equal(r.status,'ok',r.detail);assert.equal(files[P+'/result_test.json'],undefined);
let saved=JSON.parse(files[P+'/constraints.json']);
assert.deepStrictEqual(Object.keys(saved.items),['1']);assert.equal(saved.items['1'].source_name,objects[1].name);
assert.equal(saved.items['1'].lock_position,true);
// Releasing the same object deletes only that object's rule.
r=JSON.parse(context.kikiCepSetSelectedRules('/project',false,'global'));
assert.equal(r.status,'ok',r.detail);assert.deepStrictEqual(Object.keys(JSON.parse(files[P+'/constraints.json']).items),[]);
// A non-exported object must fail closed.
selection[0].uuid='non-exported';
r=JSON.parse(context.kikiCepSetSelectedRules('/project',true,'0'));
assert.equal(r.status,'error');
assert.deepStrictEqual(Object.keys(JSON.parse(files[P+'/constraints.json']).items),[]);
// Stale bounds must fail closed.
selection[0].uuid='uuid-1';selection[0].geometricBounds[0]+=1;
r=JSON.parse(context.kikiCepSetSelectedRules('/project',true,'0'));
assert.equal(r.status,'error');
console.log('PASS CEP visual-constraint matching, deletion, and fail-closed checks');
