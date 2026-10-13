/* Node-based ExtendScript smoke test. This mocks Illustrator APIs; it is NOT
   a substitute for running the scripts in Illustrator itself. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const root = path.resolve(__dirname,'..','illustrator');
function jsx(file) {
  return fs.readFileSync(path.join(root,'json_helpers.jsxinc'),'utf8')+'\n'+
    fs.readFileSync(path.join(root,'language.jsxinc'),'utf8')+'\n'+
    fs.readFileSync(path.join(root,'workspace.jsxinc'),'utf8')+'\n'+
    fs.readFileSync(path.join(root,'bridge_receipt.jsxinc'),'utf8')+'\n'+
    fs.readFileSync(path.join(root,file),'utf8')
      .replace(/^\uFEFF?#(?:target|include).*$/mg,'');
}
function makePath(name, x, y, w=12, h=8) {
  const anchors=[[x,y],[x+w,y],[x+w,y-h],[x,y-h]];
  return {typename:'PathItem',name,editable:true,hidden:false,locked:false,
    clipping:false,closed:true,filled:true,stroked:false,guides:false,
    geometricBounds:[x,y,x+w,y-h],
    pathPoints:anchors.map(a=>({anchor:a,leftDirection:a,rightDirection:a})),
    translate(dx,dy) {
      this.geometricBounds=[this.geometricBounds[0]+dx,this.geometricBounds[1]+dy,
        this.geometricBounds[2]+dx,this.geometricBounds[3]+dy];
    },
    rotate(degrees) {assert.strictEqual(degrees,0);}
  };
}
function group(name, children=[]) {
  return {typename:'GroupItem',name,editable:true,hidden:false,locked:false,clipped:false,
    pageItems:children,geometricBounds:[10,15,35,-5],
    translate(dx,dy) {
      this.geometricBounds=[this.geometricBounds[0]+dx,this.geometricBounds[1]+dy,
        this.geometricBounds[2]+dx,this.geometricBounds[3]+dy];
    },
    rotate(degrees) {assert.strictEqual(degrees,0);}
  };
}
function testExport() {
  const nestedEmpty = group('empty nested');
  const topEmpty = group('top empty');
  const main = group('family',[nestedEmpty,makePath('emblem',10,15)]);
  const second=makePath('standalone',50,15);
  const selected=[main,topEmpty,second];
  const artboards=[{artboardRect:[0,100,145*72/25.4,100-95*72/25.4]}];
  artboards.getActiveArtboardIndex=()=>0;
  const doc={name:'P10_TEST.ai',selection:selected,artboards};
  let json, alerts=[];
  const File={saveDialog:()=>({encoding:'',open:()=>true,
    write(v){json=v;},close(){}})};
  const context={app:{documents:[doc],activeDocument:doc},File,
    alert(s){alerts.push(s);},Error,isFinite,Math,String,Number,RegExp};
  vm.runInNewContext(jsx('export_selection.jsx'),context);
  assert.ok(!alerts.some(s=>/ERROR/.test(s)),alerts.join(';'));
  const data=JSON.parse(json);
  assert.strictEqual(data.objects.length,2);
  assert.strictEqual(data.source_selection_count,3);
  assert.deepStrictEqual(data.objects.map(o=>o.id),['0','2']);
  assert.strictEqual(data.skipped.length,1);
  assert.strictEqual(data.skipped[0].selection_index,1);
  assert.strictEqual(data.objects[0].geometry.children.length,1);
  assert.ok(alerts[0].includes('Пропущено пустых групп: 2'));
  return {doc, data, selected};
}
function testApply(state) {
  const before=state.selected[1].geometricBounds.slice();
  const out={schema:1,document_name:state.data.document_name,
    artboard:state.data.artboard,source_selection_count:3,items:[
      {id:'0',x_mm:30,y_mm:30,rotation_deg:0,source_name:'family',source_bounds_pt:state.data.objects[0].source_bounds_pt},
      {id:'2',x_mm:70,y_mm:30,rotation_deg:0,source_name:'standalone',source_bounds_pt:state.data.objects[1].source_bounds_pt}
    ]};
  let alerts=[];
  const File={openDialog:()=>({encoding:'',open:()=>true,
    read:()=>JSON.stringify(out),close(){}})};
  const ctx={app:{documents:[state.doc],activeDocument:state.doc,redraw(){}},File,
    alert(s){alerts.push(s);},confirm(){return true;},Error,isFinite,Math,String,Number,RegExp,
    Transformation:{CENTER:0}};
  vm.runInNewContext(jsx('apply_layout.jsx'),ctx);
  assert.ok(!alerts.some(s=>/ERROR/.test(s)),alerts.join(';'));
  assert.ok(alerts[0].includes('объектов: 2'));
  assert.deepStrictEqual(state.selected[1].geometricBounds,before);
}
function testStrokeExport() {
  const outlined=makePath('outlined-closed',5,20,15,10);
  outlined.filled=false;outlined.stroked=true;outlined.strokeWidth=1.8;
  outlined.strokeCap='StrokeCap.ROUNDENDCAP';outlined.strokeJoin='StrokeJoin.BEVELENDJOIN';
  const open=makePath('open-arrow',50,20,15,10);
  open.closed=false; open.filled=false;open.stroked=true;open.strokeWidth=2.2;
  open.pathPoints=open.pathPoints.slice(0,3);
  open.strokeCap='StrokeCap.PROJECTINGENDCAP';
  const mixed=makePath('mixed',85,20,15,10);
  mixed.stroked=true; mixed.strokeWidth=1;
  const unpainted=makePath('unpainted',110,20,15,10);
  unpainted.filled=false;unpainted.stroked=false;
  const selected=[outlined,open,mixed,unpainted];
  const artboards=[{artboardRect:[0,100,145*72/25.4,100-95*72/25.4]}];
  artboards.getActiveArtboardIndex=()=>0;
  const doc={name:'P11_STROKE_TEST.ai',selection:selected,artboards};
  let json,alerts=[];
  const File={saveDialog:()=>({encoding:'',open:()=>true,write(v){json=v;},close(){}})};
  const ctx={app:{documents:[doc],activeDocument:doc},File,alert(s){alerts.push(s);},
    Error,isFinite,Math,String,Number,RegExp};
  vm.runInNewContext(jsx('export_selection.jsx'),ctx);
  assert.ok(!alerts.some(s=>/ERROR/.test(s)),alerts.join(';'));
  const data=JSON.parse(json);
  assert.deepStrictEqual(data.objects.map(o=>o.id),['0','1','2']);
  assert.strictEqual(data.source_selection_count,4);
  assert.strictEqual(data.skipped.length,1);
  assert.strictEqual(data.objects[0].geometry.type,'stroke');
  assert.strictEqual(data.objects[0].geometry.closed,true);
  assert.strictEqual(data.objects[0].geometry.cap,'round');
  assert.strictEqual(data.objects[0].geometry.join,'bevel');
  assert.strictEqual(data.objects[1].geometry.closed,false);
  assert.strictEqual(data.objects[1].geometry.cap,'square');
  assert.strictEqual(data.objects[2].geometry.type,'group');
  assert.strictEqual(data.objects[2].geometry.children.length,2);
  assert.ok(alerts[0].includes('обводки: 3'));
  console.log('PASS JSX mock export of closed/open stroke, fill+stroke and invisible path');
}
const s=testExport();testApply(s);testStrokeExport();
console.log('PASS JSX mock export/apply with nested and top-level empty groups and sparse selection indices');

// Explicit English selection remains available and preserves numerical data.
function testEnglishUI() {
  const ui=vm.runInNewContext(jsx('export_selection.jsx'),{app:{documents:[]},
    alert:s=>s,Error,isFinite,Math,String,Number,RegExp});
  const langSource=fs.readFileSync(path.join(root,'language.jsxinc'),'utf8');
  const ctx={Folder:{userData:{fsName:'/tmp'},},File:function(){},Error,RegExp,String};
  vm.runInNewContext(langSource,ctx);
  ctx.kikiLangCache='en';
  assert.ok(ctx.kikiT('export_ok',{objects:68,strokes:10,open:39,groups:5,unpainted:2,skipped:0}).includes('68 objects'));
  ctx.kikiLangCache='ru';
  assert.ok(ctx.kikiT('export_ok',{objects:68,strokes:10,open:39,groups:5,unpainted:2,skipped:0}).includes('68'));
  assert.ok(ctx.kikiT('apply_confirm').includes('Продолжить'));
  console.log('PASS bilingual RU/EN UI and interpolation');
}
testEnglishUI();

function testSavedLanguagePreference() {
  const storage={};
  function FakeFolder(p) {this.fsName=p;this.exists=!!storage['folder:'+p];this.create=()=>{storage['folder:'+p]=true;return this.exists=true;};}
  FakeFolder.userData={fsName:'/mock-user'};
  function FakeFile(p) {this.fsName=p;this.encoding='UTF-8';this.exists=Object.prototype.hasOwnProperty.call(storage,p);}
  FakeFile.prototype.open=function(mode){this.mode=mode;return true;};
  FakeFile.prototype.write=function(v){storage[this.fsName]=v;this.exists=true;};
  FakeFile.prototype.read=function(){return storage[this.fsName]||'';};
  FakeFile.prototype.close=function(){};
  const alerts=[];
  const ctx={Folder:FakeFolder,File:FakeFile,alert:s=>alerts.push(s),
             prompt:()=> '2',Error,isFinite,Math,String,Number,RegExp};
  vm.runInNewContext(jsx('set_language.jsx'),ctx);
  assert.ok(alerts[0].includes('English'),alerts[0]);
  assert.strictEqual(storage['/mock-user/KiKiModels/language.txt'],'en');
  // Fresh Illustrator invocation / fresh script context reads persisted language.
  const reloaded={Folder:FakeFolder,File:FakeFile,Error,isFinite,Math,String,Number,RegExp};
  vm.runInNewContext(fs.readFileSync(path.join(root,'language.jsxinc'),'utf8'),reloaded);
  assert.strictEqual(reloaded.kikiGetLanguage(),'en');
  assert.ok(reloaded.kikiT('apply_confirm').includes('Continue?'));
  console.log('PASS language preference saved and reused between invocations');
}
testSavedLanguagePreference();

function testWorkspaceRoundtrip() {
  const storage={}; const created={};
  function MockFolder(p) {
    this.fsName=path.posix.normalize(p);
    this.exists=!!created[this.fsName];
    this.parent=new Object(); this.parent.fsName=path.posix.dirname(this.fsName);
    this.create=()=>{created[this.fsName]=true;this.exists=true;return true;};
  }
  MockFolder.userData={fsName:'/home/user'};
  function MockFile(p) {
    this.fsName=path.posix.normalize(p);
    this.parent=new MockFolder(path.posix.dirname(this.fsName));
    Object.defineProperty(this,'exists',{get:()=>Object.hasOwn(storage,this.fsName)});
    this.encoding='';
  }
  MockFile.prototype.open=function(){return true;};
  MockFile.prototype.write=function(s){storage[this.fsName]=s;};
  MockFile.prototype.read=function(){return storage[this.fsName];};
  MockFile.prototype.remove=function(){delete storage[this.fsName];return true;};
  MockFile.prototype.close=function(){};
  MockFile.saveDialog=()=>{throw Error('Unexpected Save dialog')};
  MockFile.openDialog=()=>{throw Error('Unexpected Open dialog')};
  const selected=[makePath('one',10,15),makePath('two',40,15)];
  const artboards=[{artboardRect:[0,100,145*72/25.4,100-95*72/25.4]}];
  artboards.getActiveArtboardIndex=()=>0;
  const doc={name:'P10_TEST.ai',selection:selected,artboards};
  let alerts=[];
  const context={app:{documents:[doc],activeDocument:doc,redraw(){}},
    File:MockFile,Folder:MockFolder,$:{fileName:'/repo/illustrator/export_selection.jsx'},
    alert:s=>alerts.push(s),confirm:()=>true,Error,isFinite,Math,String,Number,RegExp,Transformation:{CENTER:0}};
  storage['/repo/workspace/P10_TEST/result_test.json']='stale';
  vm.runInNewContext(jsx('export_selection.jsx'),context);
  const exportPath='/repo/workspace/P10_TEST/input_copy.json';
  assert.ok(storage[exportPath],alerts.join(';'));
  assert.ok(!Object.hasOwn(storage,'/repo/workspace/P10_TEST/result_test.json'));
  assert.ok(alerts[0].includes(exportPath));
  const source=JSON.parse(storage[exportPath]);
  storage['/repo/workspace/P10_TEST/result_test.json']=JSON.stringify({
    schema:1,document_name:source.document_name,
    artboard:source.artboard,source_selection_count:2,
    items:source.objects.map((x,i)=>({id:x.id,source_name:x.name,
      source_bounds_pt:x.source_bounds_pt,x_mm:10+i*25,y_mm:10,rotation_deg:0}))
  });
  context.$.fileName='/repo/illustrator/apply_layout.jsx';
  vm.runInNewContext(jsx('apply_layout.jsx'),context);
  assert.ok(alerts.at(-1).includes('размещено объектов: 2'),alerts.join(';'));
  console.log('PASS workspace auto-export, invalidate old results, and auto-apply without file dialogs');
}
testWorkspaceRoundtrip();
