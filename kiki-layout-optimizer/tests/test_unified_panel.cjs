/* Browser-independent CEP mock: check controls, export, presets and worker flow. */
const assert=require('assert'),fs=require('fs'),path=require('path'),os=require('os'),vm=require('vm');
const src=fs.readFileSync('cep/com.kikimodels.layoutoptimizer/panel.js','utf8');
const html=fs.readFileSync('cep/com.kikimodels.layoutoptimizer/index.html','utf8');
const ids=Array.from(html.matchAll(/\bid="([^"]+)"/g),x=>x[1]);
const fakeRoot=fs.mkdtempSync(path.join(os.tmpdir(),'kiki-panel-test-'));
fs.mkdirSync(path.join(fakeRoot,'.venv','Scripts'),{recursive:true});
fs.writeFileSync(path.join(fakeRoot,'.venv','Scripts','python.exe'),'mock');
const input=path.join(fakeRoot,'workspace','P10','input_copy.json');
fs.mkdirSync(path.dirname(input),{recursive:true});fs.writeFileSync(input,'{}');
function element(){return {
 textContent:'',style:{},className:'',disabled:false,checked:false,value:'',src:'',
 options:[],listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},click(){this.listeners.click();},
 remove(index){this.options.splice(index,1);},appendChild(child){this.options.push(child);},
 removeAttribute(s){delete this[s];},scrollHeight:100,scrollTop:0
};}
const elements=Object.fromEntries(ids.map(id=>[id,element()]));
for(const k of ['operation','mode','families','rotation','flow','travel','ruleRotation']){
 const counts={operation:2,mode:3,families:3,rotation:3,flow:3,travel:4,ruleRotation:4};
 elements[k].options=Array.from({length:counts[k]},()=>element());}
elements.operation.value='engrave';elements.mode.value='uniform';elements.families.value='named';
elements.rotation.value='0';elements.flow.value='free';elements.travel.value='nearest';elements.ruleRotation.value='0';
for(const k of ['gap','margin_left','margin_top','margin_right','margin_bottom'])elements[k].value=k==='gap'?'0.8':'2';
elements.kerf.value='0.15';elements.trials.value='3';elements.timeBudget.value='35';elements.seed.value='42';elements.contourAnchors.checked=false;
let workerObject=null, calls=[];
const EventEmitter=require('events');
function spawnStub(cmd,args,opts){
 assert(args.includes('kiki_layout.cep_worker'));assert(opts.cwd===fakeRoot);
 const p=new EventEmitter();p.stdout=new EventEmitter();p.stderr=new EventEmitter();p.stdout.setEncoding=()=>{};p.stderr.setEncoding=()=>{};
 p.kill=()=>{p.emit('close',null);};workerObject=p;return p;}
const document={documentElement:{lang:'ru'},getElementById:id=>elements[id]||null,
 querySelector:s=>{const match=s.match(/data-i18n="([^"]+)"/);if(!match || html.indexOf('data-i18n="'+match[1]+'"')===-1)return null;return elements['_label_'+match[1]]||(elements['_label_'+match[1]]=element());},
 createElement:()=>element()};
const context={document,window:{KIKI_PROJECT_ROOT:fakeRoot,addEventListener(){},__adobe_cep__:{evalScript(code,cb){calls.push(code);
 if(code.startsWith('kikiCepRules'))return cb(JSON.stringify({status:'ok',detail:'saved'}));
 if(code.indexOf('"export"')!==-1)return cb(JSON.stringify({status:'ok',detail:'exported',path:input}));
 return cb(JSON.stringify({status:'ok',detail:'applied',path:''}));},},cep_node:{require:(name)=>name==='child_process'?{spawn:spawnStub}:require(name)}},
 cep_node:{require:(name)=>name==='child_process'?{spawn:spawnStub}:require(name)},
 navigator:{platform:'Win32'},JSON,Date,Math,Number,Array,Object,String,isFinite,Error,console};
vm.runInNewContext(src,context);
assert.strictEqual(elements.export.textContent,'Экспорт выделения');
assert.strictEqual(elements.mode.options.length,3,'i18n must not remove select options');
elements.export.click();
assert(elements.documentName.textContent.indexOf('P10')!==-1);
elements.presetName.value='P10 Test';elements.savePreset.click();
assert(fs.existsSync(path.join(fakeRoot,'presets','P10 Test.json')));
elements.presets.value='P10 Test.json';elements.loadPreset.click();
elements.calculate.click();
assert(workerObject,'Must spawn worker');assert.strictEqual(elements.cancel.className,'danger');
assert.strictEqual(elements.mode.options[0].textContent,'Равномерно','mode labels localized');
assert(elements.outlineAware.disabled,'outline extra matcher disabled unless grouping by silhouette');
elements.families.value='auto'; elements.families.listeners.change();
assert(!elements.outlineAware.disabled,'outline extra matcher enabled for silhouette grouping');
const final=path.join(fakeRoot,'workspace','P10','result_test.json');
const preview=path.join(fakeRoot,'workspace','P10','preview_test.svg');
fs.writeFileSync(final,'{}');fs.writeFileSync(preview,'<svg xmlns="http://www.w3.org/2000/svg"/>');
workerObject.stdout.emit('data',JSON.stringify({kind:'progress',stage:'placing',done:5,total:10,percent:42})+'\n');
assert.strictEqual(elements.progressFill.style.width,'42%');
workerObject.stdout.emit('data',JSON.stringify({kind:'complete',percent:100,report:{object_count:68,cluster_count:54,min_clearance_mm:0.8,occupied_bbox_mm2:5000,within_margins:true,warnings:[],family_audit:[{label:'14',members:[{id:'17',name:'item-17',equivalent_mm:3.0},{id:'18',name:'P10-SYM-009__5.5mm',equivalent_mm:5.5}]}]},folder:path.dirname(input),result:final,preview:preview})+'\n');
workerObject.emit('close',0);
assert.strictEqual(elements.progressFill.style.width,'100%');
assert.strictEqual(elements.preview.className,'');
assert(elements.report.textContent.indexOf('68')!==-1);
assert(elements.report.textContent.includes('68 объектов'),'report metrics should be localized');
assert(elements.familyReviewContent.textContent.includes('Семейство 1'));
assert(elements.familyReviewContent.textContent.includes('SYM-009'));
assert(!elements.familyReviewContent.textContent.includes('item-17'),'user default hides technical names');
elements.showFamilyIds.checked=true;elements.showFamilyIds.listeners.change();
assert(elements.familyReviewContent.textContent.includes('item-17'),'advanced view shows original names');
elements.lang.click();assert(elements.familyReviewContent.textContent.includes('Family 1'),'family audit responds to locale');
elements.lang.click();
elements.apply.click();
assert(elements.status.textContent.indexOf('applied')!==-1);
elements.lang.click();assert.strictEqual(elements.export.textContent,'Export selection');
console.log('PASS Unified CEP mock: export -> presets -> headless job -> progress -> SVG -> apply -> locale');
