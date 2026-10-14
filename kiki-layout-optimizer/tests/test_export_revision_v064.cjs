// Re-export must migrate only unchanged Illustrator UUID geometry and audit drops.
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const base=path.resolve(__dirname,'../illustrator');
const src=['json_helpers.jsxinc','language.jsxinc','workspace.jsxinc','bridge_receipt.jsxinc','export_selection.jsx']
  .map(f=>fs.readFileSync(path.join(base,f),'utf8').replace(/^\uFEFF?#(?:target|include).*$/mg,'')).join('\n');
const storage={};const directories={};
function Folder(p){this.fsName=path.posix.normalize(p);this.parent={fsName:path.posix.dirname(this.fsName)};this.exists=!!directories[this.fsName];this.create=()=>{directories[this.fsName]=true;this.exists=true;return true;};}
Folder.userData={fsName:'/user'};
function File(p){this.fsName=path.posix.normalize(p);this.parent=new Folder(path.posix.dirname(this.fsName));this.encoding='';Object.defineProperty(this,'exists',{get:()=>Object.hasOwn(storage,this.fsName)});}
File.prototype.open=function(){return true;};File.prototype.read=function(){return storage[this.fsName];};File.prototype.write=function(s){storage[this.fsName]=s;};File.prototype.close=function(){};File.prototype.remove=function(){delete storage[this.fsName];return true;};
File.saveDialog=()=>{throw Error('Unexpected dialog');};
function item(uuid,name,x,width=5){const nodes=[[x,15],[x+width,15],[x+width,10],[x,10]];return {uuid,name,typename:'PathItem',editable:true,hidden:false,locked:false,clipping:false,closed:true,filled:true,stroked:false,guides:false,geometricBounds:[x,15,x+width,10],pathPoints:nodes.map(a=>({anchor:a,leftDirection:a,rightDirection:a}))};}
const a=item('uuid-a','A',12),b=item('uuid-b','B',28);
const boards=[{artboardRect:[0,100,411, -169.29]}];boards.getActiveArtboardIndex=()=>0;
const doc={name:'P11_COPY.ai',selection:[a,b],artboards:boards};
const ctx={app:{documents:[doc],activeDocument:doc},File,Folder,$:{fileName:'/project/illustrator/export_selection.jsx'},alert:(s)=>{if(String(s).includes('ERROR'))throw Error(String(s));},Error,isFinite,Math,String,Number,RegExp,Date};
function exportNow(){vm.runInNewContext(src,ctx);}
const dir='/project/workspace/P11_COPY';
const input=dir+'/input_copy.json',rules=dir+'/constraints.json';
exportNow();const initial=JSON.parse(storage[input]);
storage[rules]=JSON.stringify({schema:1,document_name:doc.name,items:{'0':{source_name:'A',source_bounds_pt:initial.objects[0].source_bounds_pt,lock_position:true,rotations:[0]}}});
storage[dir+'/result_test.json']='stale';
doc.selection=[b,a];exportNow();
const migrated=JSON.parse(storage[rules]);assert.deepStrictEqual(Object.keys(migrated.items),['1']);assert.equal(migrated.items['1'].source_name,'A');
assert.equal(storage[dir+'/result_test.json'],undefined);
let audit=JSON.parse(storage[dir+'/export_audit.json']);assert.equal(audit.preserved,1);assert.equal(audit.reset.length,0);
// Change A's shape and bounds; previous lock must NOT be silently reused.
a.geometricBounds=[12,15,18,10];a.pathPoints[1].anchor=[18,15];a.pathPoints[1].leftDirection=[18,15];a.pathPoints[1].rightDirection=[18,15];
exportNow();audit=JSON.parse(storage[dir+'/export_audit.json']);assert.equal(audit.preserved,0);assert.equal(audit.reset[0].reason,'geometry_changed');
assert.deepStrictEqual(Object.keys(JSON.parse(storage[rules]).items),[]);
assert(Object.keys(storage).some(k=>k.includes('/history/')&&k.endsWith('_constraints.json')),'must archive old constraints');
console.log('PASS repeated export: UUID migration, stale result reset, geometry change invalidation, history archive');
